import re
from collections import Counter

import pandas as pd
from pymongo import MongoClient
from django.http import JsonResponse


# ==============================
# MONGODB
# ==============================

client = MongoClient("mongodb+srv://rotemba3_db_user:12345@dataoilscollect.bje8esi.mongodb.net/")
db = client["DataCollectionOil"]

collection = db["modeltrainig"]
predictions_collection = db["oil_predictions"]


# ==============================
# LOAD DATA
# ==============================

def load_df():
    data = list(collection.find({}, {"_id": 0}))
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["oil_price", "oil_price_yesterday", "gas_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["text"] = df["text"].fillna("").astype(str)
    df["publisher"] = df["publisher"].fillna("EMPTY").astype(str)
    df["has_tweet"] = (df["text"].str.upper() != "EMPTY").astype(int)

    return df


# ==============================
# COMMON WORDS
# ==============================

def graph_common_words(request):
    df = load_df()

    if df.empty:
        return JsonResponse([], safe=False)

    stopwords = {
        "the", "and", "to", "of", "in", "a", "for", "on", "is", "that", "with",
        "this", "it", "at", "as", "are", "be", "by", "from", "an", "or", "we",
        "our", "will", "has", "have", "was", "were", "their", "they", "you",
        "your", "his", "her", "he", "she", "them", "about", "after", "before",
        "but", "not", "all", "more", "one", "today", "yesterday", "empty",
        "amp", "rt", "i", "my", "me", "us"
    }

    tweet_texts = df[df["has_tweet"] == 1]["text"]

    all_words = []

    for text in tweet_texts:
        words = re.findall(r"\b[a-zA-Z']+\b", text.lower())
        words = [w for w in words if w not in stopwords and len(w) > 2]
        all_words.extend(words)

    word_counts = Counter(all_words)
    top_words = word_counts.most_common(20)

    result = [{"word": word, "count": count} for word, count in top_words]

    return JsonResponse(result, safe=False)


# ==============================
# TWEETS VS OIL
# ==============================

def graph_tweets_vs_oil(request):
    df = load_df()

    if df.empty:
        return JsonResponse([], safe=False)

    daily = (
        df.groupby("date", as_index=False)
        .agg(
            tweet_count=("has_tweet", "sum"),
            oil_price=("oil_price", "first")
        )
        .dropna(subset=["date", "oil_price"])
    )

    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")

    return JsonResponse(daily.to_dict(orient="records"), safe=False)


# ==============================
# TWEETS VS OIL BY PUBLISHER
# ==============================

def graph_tweets_vs_oil_by_publisher(request):
    df = load_df()

    if df.empty:
        return JsonResponse({}, safe=False)

    tweet_rows = df[df["has_tweet"] == 1].copy()

    publishers = sorted([
        p for p in tweet_rows["publisher"].unique()
        if p != "EMPTY"
    ])

    result = {}

    for publisher in publishers:
        pub_df = tweet_rows[tweet_rows["publisher"] == publisher].copy()

        daily_pub = (
            pub_df.groupby("date", as_index=False)
            .agg(
                tweet_count=("text", "count"),
                oil_price=("oil_price", "first")
            )
            .dropna(subset=["date", "oil_price"])
        )

        daily_pub["date"] = daily_pub["date"].dt.strftime("%Y-%m-%d")

        result[publisher] = daily_pub.to_dict(orient="records")

    return JsonResponse(result, safe=False)


# ==============================
# LATEST PREDICTION
# ==============================

def get_latest_prediction(request):
    latest = predictions_collection.find_one(
        {},
        sort=[
            ("created_at", -1),
            ("prediction_date", -1),
            ("target_date", -1)
        ]
    )

    if not latest:
        return JsonResponse({
            "error": "No predictions yet",
            "count": predictions_collection.count_documents({})
        })

    latest["_id"] = str(latest["_id"])

    return JsonResponse(latest, safe=False)


# ==============================
# PREDICTION ACCURACY HISTORY
# ==============================

def graph_prediction_accuracy(request):
    data = list(
        predictions_collection.find(
            {"actual_price": {"$ne": None}},
            {"_id": 0}
        ).sort("target_date", 1)
    )

    result = []

    for item in data:
        result.append({
            "target_date": item.get("target_date"),

            "predicted_bin": item.get("predicted_bin"),
            "predicted_range": item.get("predicted_range"),

            "actual_price": item.get("actual_price"),
            "actual_bin": item.get("actual_bin"),
            "actual_range": item.get("actual_range"),

            "is_correct": 1 if item.get("is_correct") else 0,
        })

    return JsonResponse(result, safe=False)
##added by rotem
def get_all_data(request):
    df = load_df()
    print(f"DEBUG: Found {len(df)} rows in MongoDB")
    if df.empty:
        return JsonResponse([], safe=False)
    
    df = df.fillna("")

    df = df.sort_values(by="date", ascending=False)
    
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    
    return JsonResponse(df.to_dict(orient="records"), safe=False)
