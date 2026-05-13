import re
import warnings
import pandas as pd
import numpy as np

from textblob import TextBlob

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer

warnings.filterwarnings("ignore")


# ==============================
# LOAD DATA
# ==============================

file_path = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles\tweets_oil_gas_combined.csv"

df = pd.read_csv(file_path, encoding="utf-8-sig")

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["oil_price"] = pd.to_numeric(df["oil_price"], errors="coerce")

df = df.dropna(subset=["date", "oil_price"])

df["text"] = df["text"].fillna("EMPTY").astype(str)
df["publisher"] = df["publisher"].fillna("EMPTY").astype(str)


# ==============================
# TRANSLATION
# ==============================

USE_TRANSLATION = True

try:
    from langdetect import detect
    from deep_translator import GoogleTranslator

    TRANSLATION_AVAILABLE = True
    print("Translation tools loaded.")
except Exception:
    TRANSLATION_AVAILABLE = False
    print("Translation tools not installed. Continuing without translation.")
    print("To enable translation: pip install langdetect deep-translator")


translation_cache = {}


def translate_to_english(text):
    if text == "EMPTY":
        return "EMPTY"

    text = str(text).strip()

    if text == "":
        return "EMPTY"

    if not USE_TRANSLATION or not TRANSLATION_AVAILABLE:
        return text

    if text in translation_cache:
        return translation_cache[text]

    try:
        lang = detect(text)

        if lang != "en":
            translated = GoogleTranslator(source="auto", target="en").translate(text)
            translation_cache[text] = translated
            return translated

        translation_cache[text] = text
        return text

    except Exception:
        translation_cache[text] = text
        return text


print("Translating non-English tweets if needed...")
df["text_en"] = df["text"].apply(translate_to_english)


# ==============================
# TEXT CLEANING
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


df["clean_text"] = df["text_en"].apply(clean_text)


# ==============================
# SENTIMENT
# ==============================

def get_sentiment(text):
    if text == "EMPTY":
        return 0.0

    try:
        return TextBlob(str(text)).sentiment.polarity
    except Exception:
        return 0.0


df["sentiment"] = df["text_en"].apply(get_sentiment)


# ==============================
# TOP PUBLISHERS
# ==============================

top_publishers = (
    df[df["publisher"] != "EMPTY"]["publisher"]
    .value_counts()
    .head(10)
    .index
    .tolist()
)

print("Top publishers used:", top_publishers)


# ==============================
# TOPIC GROUPS
# ==============================

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


def count_topic_words(text, words):
    if text == "EMPTY":
        return 0

    tokens = text.split()
    return sum(1 for token in tokens if token in words)


def count_aggressive_words(text):
    if text == "EMPTY":
        return 0

    tokens = text.split()
    return sum(1 for token in tokens if token in aggressive_words)


# ==============================
# DAILY FEATURES
# ==============================

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
        row[f"{topic_name}_topic_count"] = count_topic_words(all_text, words)

    aggressive_count = count_aggressive_words(all_text)
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
daily = daily.sort_values("date").reset_index(drop=True)


# ==============================
# 3-DAY WINDOW FEATURES
# Day D-2 + D-1 + D -> predict Day D+1 price bin
# ==============================

window_rows = []

count_features = [
    "tweet_count",
    "positive_tweets",
    "negative_tweets",
    "neutral_tweets",
    "aggressive_count",
    "aggressive_present"
]

topic_features = [f"{topic}_topic_count" for topic in topic_groups.keys()]
publisher_count_features = [f"{p}_count" for p in top_publishers]

sentiment_features = [
    "avg_sentiment",
    "min_sentiment",
    "max_sentiment",
    "sentiment_std",
    "aggressive_ratio"
]

publisher_sentiment_features = [f"{p}_avg_sentiment" for p in top_publishers]

for i in range(len(daily)):
    if i < 2:
        continue

    if i + 1 >= len(daily):
        continue

    last_3 = daily.iloc[i-2:i+1]

    row = {}
    row["date"] = daily.loc[i, "date"]

    for col in count_features + topic_features + publisher_count_features:
        row[f"last3_{col}"] = last_3[col].sum()

    for col in sentiment_features + publisher_sentiment_features:
        row[f"last3_{col}"] = last_3[col].mean()

    current_3_count = last_3["tweet_count"].sum()

    if i >= 5:
        previous_3_count = daily.iloc[i-5:i-2]["tweet_count"].sum()
        row["last3_tweet_change"] = current_3_count - previous_3_count
    else:
        row["last3_tweet_change"] = 0

    total_topic_count = sum(row[f"last3_{col}"] for col in topic_features)
    row["last3_total_topic_count"] = total_topic_count

    for col in topic_features:
        row[f"last3_{col}_ratio"] = (
            row[f"last3_{col}"] / total_topic_count
            if total_topic_count > 0 else 0
        )

    # Light oil-history features only from the previous 3 input days.
    # These are allowed because they are known before predicting tomorrow.
    row["last3_oil_price_avg"] = last_3["oil_price"].mean()
    row["last3_oil_price_min"] = last_3["oil_price"].min()
    row["last3_oil_price_max"] = last_3["oil_price"].max()
    row["last3_oil_price_std"] = last_3["oil_price"].std() if len(last_3) > 1 else 0
    row["last3_oil_price_change"] = last_3["oil_price"].iloc[-1] - last_3["oil_price"].iloc[0]

    row["last3_text"] = " ".join(last_3["daily_text"].astype(str))

    # target = tomorrow's oil price
    row["tomorrow_oil_price"] = daily.loc[i + 1, "oil_price"]

    window_rows.append(row)


model_df = pd.DataFrame(window_rows)


# ==============================
# TARGET: 4 PRICE RANGES
# ==============================

model_df["price_bin"] = pd.qcut(
    model_df["tomorrow_oil_price"],
    q=4,
    labels=False,
    duplicates="drop"
)

print("\nPrice bin ranges:")
ranges = pd.qcut(
    model_df["tomorrow_oil_price"],
    q=4,
    duplicates="drop"
)

bin_table = pd.DataFrame({
    "bin": model_df["price_bin"],
    "price_range": ranges.astype(str)
}).drop_duplicates().sort_values("bin")

print(bin_table.to_string(index=False))

print("\nClass distribution:")
print(model_df["price_bin"].value_counts().sort_index())


# ==============================
# TEXT FEATURES
# ==============================

tfidf = TfidfVectorizer(
    max_features=150,
    stop_words="english",
    lowercase=True,
    min_df=1
)

text_features = tfidf.fit_transform(model_df["last3_text"]).toarray()
text_feature_names = [f"word_{word}" for word in tfidf.get_feature_names_out()]

text_df = pd.DataFrame(text_features, columns=text_feature_names)


# ==============================
# FINAL X / y
# ==============================

exclude_cols = [
    "date",
    "last3_text",
    "tomorrow_oil_price",
    "price_bin"
]

numeric_df = model_df.drop(columns=exclude_cols).fillna(0)

X_df = pd.concat(
    [
        numeric_df.reset_index(drop=True),
        text_df.reset_index(drop=True)
    ],
    axis=1
)

X = X_df.values
y = model_df["price_bin"].values

print("\nFinal ML dataset:")
print("Rows:", X_df.shape[0])
print("Features:", X_df.shape[1])
print("Target: tomorrow oil price bin, 4 ranges")
print("Time features removed: YES")
print("Oil price features included lightly: YES")


# ==============================
# MODELS
# ==============================

models = {
    "Logistic Regression": LogisticRegression(max_iter=3000),
    "Random Forest": RandomForestClassifier(n_estimators=300, random_state=42),
    "Extra Trees": ExtraTreesClassifier(n_estimators=300, random_state=42),
    "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, random_state=42),
    "SVC": SVC(kernel="rbf", C=10)
}


splits = {
    "80-20": 0.20,
    "70-30": 0.30,
    "60-40": 0.40
}


# ==============================
# TRAIN + EVALUATE
# ==============================

results = []

for split_name, test_size in splits.items():
    print("\n==============================")
    print(f"Split {split_name}")
    print("==============================")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
        stratify=y
    )

    for model_name, model in models.items():
        model.fit(X_train, y_train)

        preds = model.predict(X_test)

        acc = accuracy_score(y_test, preds)
        f1_macro = f1_score(y_test, preds, average="macro")
        f1_weighted = f1_score(y_test, preds, average="weighted")

        results.append({
            "split": split_name,
            "model": model_name,
            "accuracy": acc,
            "f1_macro": f1_macro,
            "f1_weighted": f1_weighted
        })

        print(f"{model_name}")
        print(f"  Accuracy:    {acc:.4f}")
        print(f"  F1 macro:    {f1_macro:.4f}")
        print(f"  F1 weighted: {f1_weighted:.4f}")


# ==============================
# SUMMARY
# ==============================

results_df = pd.DataFrame(results)

print("\n==============================")
print("FINAL COMPARISON")
print("==============================")

print(
    results_df
    .sort_values(["split", "accuracy"], ascending=[True, False])
    .to_string(index=False)
)

print("\n==============================")
print("PIVOT: ACCURACY")
print("==============================")

print(
    results_df.pivot(
        index="model",
        columns="split",
        values="accuracy"
    )
)

best = results_df.sort_values("accuracy", ascending=False).iloc[0]

print("\n==============================")
print("BEST MODEL")
print("==============================")
print(best)


# ==============================
# DETAILED REPORT FOR BEST MODEL
# ==============================

best_model_name = best["model"]
best_split = best["split"]
best_test_size = splits[best_split]

best_model = models[best_model_name]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=best_test_size,
    random_state=42,
    stratify=y
)

best_model.fit(X_train, y_train)
best_preds = best_model.predict(X_test)

print("\n==============================")
print(f"CLASSIFICATION REPORT: {best_model_name}, split {best_split}")
print("==============================")
print(classification_report(y_test, best_preds))


# ==============================
# FEATURE IMPORTANCE
# ==============================

importance_model = ExtraTreesClassifier(n_estimators=300, random_state=42)
importance_model.fit(X, y)

importances = pd.DataFrame({
    "feature": X_df.columns,
    "importance": importance_model.feature_importances_
}).sort_values("importance", ascending=False)

print("\n==============================")
print("TOP 40 IMPORTANT FEATURES")
print("==============================")
print(importances.head(40).to_string(index=False))
# ==============================
# SAVE BEST MODEL + ARTIFACTS
# ==============================

import joblib
import os

print("\n==============================")
print("SAVING BEST MODEL AND ARTIFACTS")
print("==============================")

BASE_DIR = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

MODEL_FILE = os.path.join(BASE_DIR, "oil_model.pkl")
TFIDF_FILE = os.path.join(BASE_DIR, "tfidf.pkl")
FEATURE_COLUMNS_FILE = os.path.join(BASE_DIR, "feature_columns.pkl")
BIN_TABLE_FILE = os.path.join(BASE_DIR, "bin_table.pkl")
TRAINING_RESULTS_FILE = os.path.join(BASE_DIR, "training_results.csv")
FEATURE_IMPORTANCE_FILE = os.path.join(BASE_DIR, "feature_importance.csv")

# Save the best trained model
joblib.dump(best_model, MODEL_FILE)

# Save the fitted TF-IDF object
joblib.dump(tfidf, TFIDF_FILE)

# Save exact feature column order
joblib.dump(X_df.columns.tolist(), FEATURE_COLUMNS_FILE)

# Save price bin table
joblib.dump(bin_table, BIN_TABLE_FILE)

# Optional but useful: save training comparison and feature importance
results_df.to_csv(TRAINING_RESULTS_FILE, index=False, encoding="utf-8-sig")
importances.to_csv(FEATURE_IMPORTANCE_FILE, index=False, encoding="utf-8-sig")

print("Saved successfully:")
print(f"- {MODEL_FILE}")
print(f"- {TFIDF_FILE}")
print(f"- {FEATURE_COLUMNS_FILE}")
print(f"- {BIN_TABLE_FILE}")
print(f"- {TRAINING_RESULTS_FILE}")
print(f"- {FEATURE_IMPORTANCE_FILE}")

print("\nBest model saved:")
print(f"Model: {best_model_name}")
print(f"Split: {best_split}")
print(f"Accuracy: {best['accuracy']:.4f}")
print(f"F1 macro: {best['f1_macro']:.4f}")
print(f"F1 weighted: {best['f1_weighted']:.4f}")