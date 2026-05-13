import os
import re
import joblib
import subprocess
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
from pymongo import MongoClient


# ==============================
# PATHS
# ==============================

BASE_DIR = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

TRAIN_SCRIPT = os.path.join(BASE_DIR, "Trainmodel.py")
DATA_FILE = os.path.join(BASE_DIR, "tweets_oil_gas_combined.csv")

MODEL_FILE = os.path.join(BASE_DIR, "oil_model.pkl")
TFIDF_FILE = os.path.join(BASE_DIR, "tfidf.pkl")
FEATURE_COLUMNS_FILE = os.path.join(BASE_DIR, "feature_columns.pkl")
BIN_TABLE_FILE = os.path.join(BASE_DIR, "bin_table.pkl")


# ==============================
# MONGODB
# ==============================

MONGO_URI = "mongodb+srv://rotemba3_db_user:12345@dataoilscollect.bje8esi.mongodb.net/"
DB_NAME = "DataCollectionOil"
PREDICTIONS_COLLECTION = "oil_predictions"


# ==============================
# OPTIONAL RETRAIN
# ==============================

def retrain_model():
    print("\n==============================")
    print("Retraining model")
    print("==============================")

    result = subprocess.run(
        ["python", TRAIN_SCRIPT],
        cwd=BASE_DIR,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError("Trainmodel.py failed. Cannot predict.")

    print("Model retrained successfully.")


# ==============================
# TEXT HELPERS
# ==============================

def clean_text(text):
    if text == "EMPTY":
        return "EMPTY"

    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = text.replace("#", "")
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else "EMPTY"


def get_sentiment(text):
    if text == "EMPTY":
        return 0.0

    try:
        return TextBlob(str(text)).sentiment.polarity
    except Exception:
        return 0.0


topic_groups = {
    "war": [
        "war", "attack", "strike", "missile", "military", "terror",
        "rocket", "bomb", "killed", "troops", "hezbollah", "hamas"
    ],
    "peace": [
        "ceasefire", "peace", "agreement", "deal", "diplomacy",
        "negotiation", "talks", "truce"
    ],
    "iran": [
        "iran", "iranian", "tehran", "hormuz", "sanctions",
        "khamenei", "islamic", "republic"
    ],
    "oil_energy": [
        "oil", "gas", "fuel", "energy", "barrel", "crude",
        "petroleum", "prices", "export"
    ],
    "usa": [
        "america", "american", "usa", "us", "trump", "whitehouse",
        "washington", "biden"
    ],
    "israel_lebanon": [
        "israel", "israeli", "idf", "lebanon", "lebanese",
        "gaza", "jerusalem", "netanyahu"
    ],
    "economy": [
        "economy", "market", "trade", "inflation", "stock",
        "dollar", "growth", "crisis"
    ]
}


aggressive_words = [
    "war", "attack", "strike", "missile", "rocket", "bomb",
    "killed", "dead", "death", "terror", "troops", "military",
    "violence", "explosion", "raid", "threat", "weapon", "weapons",
    "fire", "fired", "launch", "launched", "destroy", "destroyed"
]


def count_words(text, words):
    if text == "EMPTY":
        return 0

    tokens = text.split()
    return sum(1 for token in tokens if token in words)


# ==============================
# DAILY FEATURES
# ==============================

def build_daily_features(df, feature_columns):
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["oil_price"] = pd.to_numeric(df["oil_price"], errors="coerce")

    df = df.dropna(subset=["date", "oil_price"]).copy()

    df["text"] = df["text"].fillna("EMPTY").astype(str)
    df["publisher"] = df["publisher"].fillna("EMPTY").astype(str)

    df["clean_text"] = df["text"].apply(clean_text)
    df["sentiment"] = df["text"].apply(get_sentiment)

    publisher_names = set()

    for col in feature_columns:
        if col.startswith("last3_") and col.endswith("_count"):
            name = col.replace("last3_", "").replace("_count", "")

            if name not in [
                "tweet",
                "positive_tweets",
                "negative_tweets",
                "neutral_tweets",
                "aggressive",
                "war_topic",
                "peace_topic",
                "iran_topic",
                "oil_energy_topic",
                "usa_topic",
                "israel_lebanon_topic",
                "economy_topic",
                "total_topic",
            ]:
                publisher_names.add(name)

    top_publishers = sorted(list(publisher_names))

    daily_rows = []

    for date, group in df.groupby("date"):
        row = {}
        row["date"] = date

        real = group[group["text"] != "EMPTY"]

        row["tweet_count"] = len(real)

        row["avg_sentiment"] = real["sentiment"].mean() if len(real) > 0 else 0
        row["min_sentiment"] = real["sentiment"].min() if len(real) > 0 else 0
        row["max_sentiment"] = real["sentiment"].max() if len(real) > 0 else 0
        row["sentiment_std"] = real["sentiment"].std() if len(real) > 1 else 0

        row["positive_tweets"] = (real["sentiment"] > 0.1).sum()
        row["negative_tweets"] = (real["sentiment"] < -0.1).sum()
        row["neutral_tweets"] = (
            (real["sentiment"] >= -0.1) &
            (real["sentiment"] <= 0.1)
        ).sum()

        all_text = (
            " ".join(real["clean_text"].astype(str))
            if len(real) > 0
            else "EMPTY"
        )

        row["daily_text"] = all_text

        for topic_name, words in topic_groups.items():
            row[f"{topic_name}_topic_count"] = count_words(all_text, words)

        aggressive_count = count_words(all_text, aggressive_words)
        total_words = len(all_text.split()) if all_text != "EMPTY" else 1

        row["aggressive_count"] = aggressive_count
        row["aggressive_present"] = 1 if aggressive_count > 0 else 0
        row["aggressive_ratio"] = aggressive_count / total_words

        for publisher in top_publishers:
            p_group = real[real["publisher"] == publisher]

            row[f"{publisher}_count"] = len(p_group)
            row[f"{publisher}_avg_sentiment"] = (
                p_group["sentiment"].mean() if len(p_group) > 0 else 0
            )

        row["oil_price"] = group["oil_price"].iloc[0]

        daily_rows.append(row)

    daily = pd.DataFrame(daily_rows)

    if daily.empty:
        raise ValueError("No valid daily rows were created from the CSV.")

    daily = daily.sort_values("date").reset_index(drop=True)

    return daily


# ==============================
# LAST 3 DAYS PREDICTION ROW
# ==============================

def build_prediction_row(daily, feature_columns):
    if len(daily) < 3:
        raise ValueError("Need at least 3 days of data to predict tomorrow.")

    last_3 = daily.tail(3)

    row = {}

    count_features = [
        "tweet_count",
        "positive_tweets",
        "negative_tweets",
        "neutral_tweets",
        "aggressive_count",
        "aggressive_present",
    ]

    topic_features = [f"{topic}_topic_count" for topic in topic_groups.keys()]

    sentiment_features = [
        "avg_sentiment",
        "min_sentiment",
        "max_sentiment",
        "sentiment_std",
        "aggressive_ratio",
    ]

    publisher_count_features = [
        col.replace("last3_", "").replace("_count", "")
        for col in feature_columns
        if col.startswith("last3_") and col.endswith("_count")
    ]

    publisher_count_features = [
        f"{publisher}_count"
        for publisher in publisher_count_features
        if f"{publisher}_count" in daily.columns
    ]

    publisher_sentiment_features = [
        col.replace("last3_", "")
        for col in feature_columns
        if col.startswith("last3_") and col.endswith("_avg_sentiment")
    ]

    publisher_sentiment_features = [
        col for col in publisher_sentiment_features
        if col in daily.columns
    ]

    for col in count_features + topic_features + publisher_count_features:
        if col in daily.columns:
            row[f"last3_{col}"] = last_3[col].sum()

    for col in sentiment_features + publisher_sentiment_features:
        if col in daily.columns:
            row[f"last3_{col}"] = last_3[col].mean()

    current_3_count = last_3["tweet_count"].sum()

    if len(daily) >= 6:
        previous_3_count = daily.iloc[-6:-3]["tweet_count"].sum()
        row["last3_tweet_change"] = current_3_count - previous_3_count
    else:
        row["last3_tweet_change"] = 0

    total_topic_count = sum(
        row.get(f"last3_{col}", 0)
        for col in topic_features
    )

    row["last3_total_topic_count"] = total_topic_count

    for col in topic_features:
        row[f"last3_{col}_ratio"] = (
            row.get(f"last3_{col}", 0) / total_topic_count
            if total_topic_count > 0
            else 0
        )

    row["last3_oil_price_avg"] = last_3["oil_price"].mean()
    row["last3_oil_price_min"] = last_3["oil_price"].min()
    row["last3_oil_price_max"] = last_3["oil_price"].max()
    row["last3_oil_price_std"] = (
        last_3["oil_price"].std() if len(last_3) > 1 else 0
    )
    row["last3_oil_price_change"] = (
        last_3["oil_price"].iloc[-1] - last_3["oil_price"].iloc[0]
    )

    last3_text = " ".join(last_3["daily_text"].astype(str))

    return row, last3_text, last_3


# ==============================
# MODEL INPUT
# ==============================

def build_model_input(row, last3_text, tfidf, feature_columns):
    numeric_df = pd.DataFrame([row]).fillna(0)

    text_features = tfidf.transform([last3_text]).toarray()
    text_feature_names = [f"word_{word}" for word in tfidf.get_feature_names_out()]
    text_df = pd.DataFrame(text_features, columns=text_feature_names)

    full_df = pd.concat(
        [
            numeric_df.reset_index(drop=True),
            text_df.reset_index(drop=True),
        ],
        axis=1
    )

    X_input = full_df.reindex(columns=feature_columns, fill_value=0)

    return X_input


# ==============================
# PRICE BIN / RANGE HELPERS
# ==============================

def get_bin_for_price(price, bin_table):
    price = float(price)

    for _, row in bin_table.iterrows():
        bin_number = int(row["bin"])
        price_range = str(row["price_range"])

        cleaned = (
            price_range
            .replace("(", "")
            .replace("[", "")
            .replace(")", "")
            .replace("]", "")
        )

        left, right = cleaned.split(",")

        left = float(left.strip())
        right = float(right.strip())

        if left < price <= right:
            return bin_number, price_range

    return None, None


# ==============================
# UPDATE OLD PREDICTIONS
# ==============================

def update_old_predictions_with_actual_prices(daily, bin_table):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[PREDICTIONS_COLLECTION]

    daily_lookup = {}

    for _, row in daily.iterrows():
        date_str = str(row["date"].date())
        daily_lookup[date_str] = float(row["oil_price"])

    pending_predictions = list(collection.find({
        "actual_price": None
    }))

    print("\n==============================")
    print("UPDATING OLD PREDICTIONS")
    print("==============================")
    print("Pending predictions:", len(pending_predictions))

    updated_count = 0

    for prediction in pending_predictions:
        target_date = prediction.get("target_date")

        if target_date not in daily_lookup:
            print(f"No actual price yet for {target_date}")
            continue

        actual_price = daily_lookup[target_date]

        actual_bin, actual_range = get_bin_for_price(
            actual_price,
            bin_table
        )

        predicted_bin = prediction.get("predicted_bin")

        is_correct = (
            actual_bin is not None and
            predicted_bin is not None and
            int(predicted_bin) == int(actual_bin)
        )

        collection.update_one(
            {"_id": prediction["_id"]},
            {
                "$set": {
                    "actual_price": actual_price,
                    "actual_bin": actual_bin,
                    "actual_range": actual_range,
                    "is_correct": is_correct,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        updated_count += 1

        print(
            f"Updated {target_date}: "
            f"actual_price={actual_price}, "
            f"actual_range={actual_range}, "
            f"correct={is_correct}"
        )

    print("Old predictions updated:", updated_count)


# ==============================
# SAVE NEW PREDICTION
# ==============================

def save_prediction_to_mongo(prediction_doc):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[PREDICTIONS_COLLECTION]

    collection.update_one(
        {"target_date": prediction_doc["target_date"]},
        {
            "$set": prediction_doc,
            "$setOnInsert": {
                "first_created_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    print("\nPrediction saved to MongoDB.")
    print(prediction_doc)


# ==============================
# MAIN
# ==============================

def main():
    # Do NOT retrain every time.
    # Only uncomment this when you intentionally want to rebuild model files.
    # retrain_model()

    print("\n==============================")
    print("Loading model artifacts")
    print("==============================")

    model = joblib.load(MODEL_FILE)
    tfidf = joblib.load(TFIDF_FILE)
    feature_columns = joblib.load(FEATURE_COLUMNS_FILE)
    bin_table = joblib.load(BIN_TABLE_FILE)

    print("Model loaded:", MODEL_FILE)
    print("Expected feature count:", len(feature_columns))

    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")

    daily = build_daily_features(df, feature_columns)

    # Step 1: update old predictions if actual oil price now exists
    update_old_predictions_with_actual_prices(daily, bin_table)

    # Step 2: create tomorrow prediction
    row, last3_text, last_3 = build_prediction_row(daily, feature_columns)

    X_input = build_model_input(
        row=row,
        last3_text=last3_text,
        tfidf=tfidf,
        feature_columns=feature_columns
    )

    print("Prediction input shape:", X_input.shape)

    if X_input.shape[1] != len(feature_columns):
        raise ValueError(
            f"Feature mismatch: X_input has {X_input.shape[1]} features, "
            f"but expected {len(feature_columns)}."
        )

    predicted_bin = int(model.predict(X_input)[0])

    range_row = bin_table[bin_table["bin"] == predicted_bin]

    if len(range_row) > 0:
        predicted_range = str(range_row.iloc[0]["price_range"])
    else:
        predicted_range = "UNKNOWN"

    latest_date = daily["date"].max().date()
    target_date = latest_date + timedelta(days=1)

    prediction_doc = {
        "prediction_date": str(datetime.today().date()),
        "target_date": str(target_date),
        "latest_data_date": str(latest_date),
        "model_file": "oil_model.pkl",

        "predicted_bin": predicted_bin,
        "predicted_range": predicted_range,

        "actual_price": None,
        "actual_bin": None,
        "actual_range": None,
        "is_correct": None,

        "last3_dates": [str(d.date()) for d in last_3["date"]],
        "created_at": datetime.utcnow()
    }

    print("\n==============================")
    print("TOMORROW PREDICTION")
    print("==============================")
    print("Latest data date:", latest_date)
    print("Target date:", target_date)
    print("Predicted range:", predicted_range)

    save_prediction_to_mongo(prediction_doc)


if __name__ == "__main__":
    main()