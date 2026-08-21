import os
import re
import joblib
import subprocess
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.offsets import BDay
from textblob import TextBlob
from pymongo import MongoClient


# ==============================
# PATHS
# ==============================

# CHANGED: relative path instead of a hardcoded Windows one.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TRAIN_SCRIPT         = os.path.join(BASE_DIR, "Trainmodel.py")

MODEL_FILE           = os.path.join(BASE_DIR, "oil_model.pkl")
TFIDF_FILE           = os.path.join(BASE_DIR, "tfidf.pkl")
FEATURE_COLUMNS_FILE = os.path.join(BASE_DIR, "feature_columns.pkl")
BIN_EDGES_FILE       = os.path.join(BASE_DIR, "bin_edges.pkl")   # <-- changed from bin_table.pkl


# ==============================
# MONGODB
# ==============================

# CHANGED: reads your existing MONGO_URI secret/env var instead of a
# hardcoded connection string.
MONGO_URI              = os.environ["MONGO_URI"]
DB_NAME                = "DataCollectionOil"
TRAINING_COLLECTION    = "modeltrainig"   # note: typo matches existing collection name
PREDICTIONS_COLLECTION = "oil_predictions"


# ==============================
# OPTIONAL RETRAIN (left as-is, unused — training is now its own separate
# weekly GitHub Actions job instead of being called from here)
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
# ADDED: DOWNLOAD MODEL ARTIFACTS FROM HUGGING FACE HUB
# ==============================
# predict_tomorrow.py now runs on a fresh GitHub Actions runner every day,
# separate from the machine train_model.py ran on. This pulls down the
# model files train_model.py last uploaded, before loading them below.

def download_artifacts():
    HF_REPO_ID = os.environ.get("HF_REPO_ID")
    HF_TOKEN   = os.environ.get("HF_TOKEN")

    if not HF_REPO_ID:
        print("HF_REPO_ID not set — assuming model files already exist locally.")
        return

    import shutil
    from huggingface_hub import hf_hub_download

    print("\n==============================")
    print("Downloading model artifacts from Hugging Face Hub")
    print("==============================")

    for filename, target in [
        ("oil_model.pkl",       MODEL_FILE),
        ("tfidf.pkl",           TFIDF_FILE),
        ("feature_columns.pkl", FEATURE_COLUMNS_FILE),
        ("bin_edges.pkl",       BIN_EDGES_FILE),
    ]:
        downloaded_path = hf_hub_download(
            repo_id=HF_REPO_ID, filename=filename, repo_type="model", token=HF_TOKEN
        )
        shutil.copy(downloaded_path, target)
        print(f"  {filename} -> {target}")


# ==============================
# TRANSLATION
# Must mirror Trainmodel.py so sentiment/topic features are built
# from the same English text representation used during training.
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

translation_cache = {}


def translate_to_english(text):
    if text is None:
        return "EMPTY"

    text = str(text).strip()

    if text == "" or text.upper() == "EMPTY":
        return "EMPTY"

    if not USE_TRANSLATION or not TRANSLATION_AVAILABLE:
        return text

    if text in translation_cache:
        return translation_cache[text]

    try:
        lang = detect(text)

        if lang != "en":
            translated = GoogleTranslator(
                source="auto",
                target="en"
            ).translate(text)

            translation_cache[text] = translated
            return translated

        translation_cache[text] = text
        return text

    except Exception:
        translation_cache[text] = text
        return text


# ==============================
# TEXT HELPERS
# ==============================

def clean_text(text):
    if text is None:
        return "EMPTY"
    text = str(text)
    if text.upper() == "EMPTY" or text.strip() == "":
        return "EMPTY"
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = text.replace("#", "")
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else "EMPTY"


def get_sentiment(text):
    if text is None:
        return 0.0
    text = str(text)
    if text.upper() == "EMPTY" or text.strip() == "":
        return 0.0
    try:
        return TextBlob(text).sentiment.polarity
    except Exception:
        return 0.0


# ==============================
# TOPIC GROUPS (must match Trainmodel.py exactly)
# ==============================

topic_groups = {
    "war": [
        "war", "attack", "strike", "missile", "military", "terror",
        "rocket", "bomb", "killed", "troops", "hezbollah", "hamas",
        "conflict", "combat", "warfare", "offensive", "assault", "airstrike",
        "invasion", "siege", "casualties", "wounded", "artillery", "drone",
        "navy", "battalion", "frontline", "rebel", "insurgent", "militia",
        "gunfire", "sniper", "mortar", "warship", "submarine", "fighter",
        "nuclear", "tactical", "hostage", "kidnap", "ambush", "guerrilla"
    ],
    "peace": [
        "ceasefire", "peace", "agreement", "deal", "diplomacy",
        "negotiation", "talks", "truce",
        "treaty", "accord", "settlement", "reconciliation", "mediation",
        "resolution", "dialogue", "summit", "bilateral", "multilateral",
        "humanitarian", "withdrawal", "deescalation", "armistice",
        "peacekeeping", "envoy", "ambassador", "cooperation", "alliance"
    ],
    "iran": [
        "iran", "iranian", "tehran", "hormuz", "sanctions",
        "khamenei", "islamic", "republic",
        "rouhani", "raisi", "irgc", "nuclear", "enrichment", "uranium",
        "strait", "persian", "gulf", "revolutionary", "guard", "proxy",
        "jcpoa", "vienna", "embargo", "ayatollah", "hardliner", "regime"
    ],
    "oil_energy": [
        "oil", "gas", "fuel", "energy", "barrel", "crude",
        "petroleum", "prices", "export",
        "opec", "brent", "wti", "refinery", "pipeline", "tanker",
        "lng", "shale", "offshore", "onshore", "drilling", "rig",
        "production", "output", "supply", "demand", "inventory",
        "stockpile", "reserve", "capacity", "quota", "cut", "pump",
        "gasoline", "diesel", "natural", "renewable", "solar", "wind",
        "coal", "nuclear", "powerplant", "electricity", "kwh", "megawatt"
    ],
    "usa": [
        "america", "american", "usa", "us", "trump", "whitehouse",
        "washington", "biden",
        "congress", "senate", "federal", "reserve", "pentagon",
        "state", "department", "cia", "democrat", "republican",
        "sanctions", "tariff", "policy", "administration", "secretary",
        "harris", "antony", "blinken", "treasury", "fed", "powell",
        "inflation", "interest", "rate", "stimulus", "deficit"
    ],
    "israel_lebanon": [
        "israel", "israeli", "idf", "lebanon", "lebanese",
        "gaza", "jerusalem", "netanyahu",
        "west", "bank", "palestine", "palestinian", "settler",
        "border", "occupation", "tel", "aviv", "haifa", "beirut",
        "south", "sinai", "golan", "hamas", "fatah", "PLO",
        "checkpoint", "blockade", "displacement", "refugee", "unrwa",
        "galilee", "beit", "iron", "dome", "knesset", "mossad"
    ],
    "economy": [
        "economy", "market", "trade", "inflation", "stock",
        "dollar", "growth", "crisis",
        "gdp", "recession", "depression", "unemployment", "jobs",
        "bond", "yield", "equity", "commodity", "forex", "currency",
        "euro", "yen", "yuan", "ruble", "debt", "deficit", "surplus",
        "budget", "fiscal", "monetary", "central", "bank", "interest",
        "rate", "hike", "cut", "quantitative", "easing", "imf",
        "worldbank", "wto", "g7", "g20", "brics", "export", "import",
        "tariff", "embargo", "supply", "chain", "logistics", "shipping"
    ],
    "russia": [
        "russia", "russian", "moscow", "putin", "kremlin", "gazprom",
        "ukraine", "ukrainian", "kiev", "kyiv", "nato", "rosneft",
        "lukashenko", "belarus", "siberia", "arctic", "nord", "stream",
        "pipeline", "ruble", "oligarch", "sanctions", "wagner"
    ],
    "china": [
        "china", "chinese", "beijing", "xi", "jinping", "ccp",
        "shanghai", "hong", "kong", "taiwan", "prc", "sinopec",
        "cnpc", "petrochina", "yuan", "renminbi", "silk", "road",
        "belt", "initiative", "south", "sea", "pacific", "asian"
    ],
    "opec": [
        "opec", "saudi", "arabia", "aramco", "riyadh", "mbs",
        "bin", "salman", "uae", "emirates", "abu", "dhabi",
        "kuwait", "qatar", "iraq", "baghdad", "libya", "tripoli",
        "nigeria", "abuja", "venezuela", "caracas", "quota",
        "production", "cut", "output", "barrel", "bpd", "cartel"
    ],
    "market_sentiment": [
        "rally", "surge", "spike", "crash", "plunge", "drop",
        "soar", "tumble", "volatile", "volatility", "bull", "bear",
        "panic", "fear", "greed", "uncertainty", "shock", "surprise",
        "rebound", "recovery", "selloff", "correction", "dip", "peak",
        "bottom", "top", "breakout", "resistance", "support", "momentum"
    ],
    "weather_natural": [
        "hurricane", "storm", "flood", "drought", "earthquake",
        "wildfire", "typhoon", "cyclone", "tornado", "blizzard",
        "pipeline", "disruption", "outage", "shutdown", "force",
        "majeure", "damage", "infrastructure", "refinery", "offshore"
    ]
}

aggressive_words = [
    "war", "attack", "strike", "missile", "rocket", "bomb",
    "killed", "dead", "death", "terror", "troops", "military",
    "violence", "explosion", "raid", "threat", "weapon", "weapons",
    "fire", "fired", "launch", "launched", "destroy", "destroyed",
    "assassinate", "assassination", "massacre", "genocide", "airstrike",
    "shelling", "bombardment", "drone", "combat", "offensive", "siege",
    "ambush", "casualties", "wounded", "conflict", "hostage", "execute",
    "executed", "detonate", "detonated", "collapse", "collapsed"
]

# All topic names — used to exclude them from being treated as publisher names
TOPIC_NAMES = set(topic_groups.keys())


def count_words(text, words):
    if text is None:
        return 0
    text = str(text)
    if text.upper() == "EMPTY":
        return 0
    tokens = text.split()
    return sum(1 for token in tokens if token in words)


# ==============================
# BIN HELPERS (uses bin_edges array, not bin_table)
# ==============================

def get_bin_for_price(price, bin_edges):
    """
    bin_edges: numpy array from pd.qcut(..., retbins=True)
    bin_edges[0] = -inf, bin_edges[-1] = +inf
    Returns (bin_index int, range_string) or (None, None)
    """
    price = float(price)
    for i in range(len(bin_edges) - 1):
        left  = bin_edges[i]
        right = bin_edges[i + 1]
        if left < price <= right:
            left_str  = "-inf" if np.isinf(left)  else f"{left:.4f}"
            right_str = "+inf" if np.isinf(right) else f"{right:.4f}"
            return i, f"({left_str}, {right_str}]"
    return None, None


def bin_label(bin_index, bin_edges):
    """Human-readable range string for a given bin index."""
    if bin_index is None or bin_index >= len(bin_edges) - 1:
        return "UNKNOWN"
    left  = bin_edges[bin_index]
    right = bin_edges[bin_index + 1]
    left_str  = "-inf" if np.isinf(left)  else f"{left:.4f}"
    right_str = "+inf" if np.isinf(right) else f"{right:.4f}"
    return f"({left_str}, {right_str}]"


# ==============================
# DAILY FEATURES
# ==============================

def build_daily_features(df, feature_columns):
    df = df.copy()
    df["date"]      = pd.to_datetime(df["date"], errors="coerce")
    df["oil_price"] = pd.to_numeric(df["oil_price"], errors="coerce")
    df = df.dropna(subset=["date", "oil_price"]).copy()
    df["text"]      = df["text"].fillna("EMPTY").astype(str)
    df["publisher"] = df["publisher"].fillna("EMPTY").astype(str)

    print("Translating non-English tweets if needed...")
    df["text_en"]    = df["text"].apply(translate_to_english)
    df["clean_text"] = df["text_en"].apply(clean_text)
    df["sentiment"]  = df["text_en"].apply(get_sentiment)

    # Derive publisher list from saved feature columns,
    # excluding any name that matches a topic or known aggregate column
    exclude_names = TOPIC_NAMES | {
        "tweet", "positive_tweets", "negative_tweets", "neutral_tweets",
        "aggressive", "total_topic",
    }
    publisher_names = set()
    for col in feature_columns:
        if col.startswith("last3_") and col.endswith("_count"):
            name = col.replace("last3_", "").replace("_count", "")
            name_clean = name.replace("_topic", "")
            if name_clean not in exclude_names and name not in exclude_names:
                publisher_names.add(name)

    top_publishers = sorted(list(publisher_names))

    daily_rows = []
    for date, group in df.groupby("date"):
        row = {}
        row["date"] = date

        real = group[group["text"].str.upper() != "EMPTY"]

        row["tweet_count"]     = len(real)
        row["avg_sentiment"]   = real["sentiment"].mean() if len(real) > 0 else 0
        row["min_sentiment"]   = real["sentiment"].min()  if len(real) > 0 else 0
        row["max_sentiment"]   = real["sentiment"].max()  if len(real) > 0 else 0
        row["sentiment_std"]   = real["sentiment"].std()  if len(real) > 1 else 0

        row["positive_tweets"] = int((real["sentiment"] >  0.1).sum())
        row["negative_tweets"] = int((real["sentiment"] < -0.1).sum())
        row["neutral_tweets"]  = int((
            (real["sentiment"] >= -0.1) & (real["sentiment"] <= 0.1)
        ).sum())

        all_text = (
            " ".join(real["clean_text"].astype(str))
            if len(real) > 0 else "EMPTY"
        )
        row["daily_text"] = all_text

        for topic_name, words in topic_groups.items():
            row[f"{topic_name}_topic_count"] = count_words(all_text, words)

        aggressive_count = count_words(all_text, aggressive_words)
        total_words      = len(all_text.split()) if all_text != "EMPTY" else 1
        row["aggressive_count"]   = aggressive_count
        row["aggressive_present"] = 1 if aggressive_count > 0 else 0
        row["aggressive_ratio"]   = aggressive_count / total_words

        for publisher in top_publishers:
            p_group = real[real["publisher"] == publisher]
            row[f"{publisher}_count"]         = len(p_group)
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
        raise ValueError("Need at least 3 days of data to predict.")

    last_3 = daily.tail(3)
    i      = daily.index.max()   # position of most recent row

    row = {}

    count_features = [
        "tweet_count", "positive_tweets", "negative_tweets",
        "neutral_tweets", "aggressive_count", "aggressive_present",
    ]
    topic_features = [f"{topic}_topic_count" for topic in topic_groups.keys()]
    sentiment_features = [
        "avg_sentiment", "min_sentiment", "max_sentiment",
        "sentiment_std", "aggressive_ratio",
    ]

    # Derive publisher feature lists from saved columns
    publisher_count_features     = []
    publisher_sentiment_features = []
    for col in feature_columns:
        if col.startswith("last3_") and col.endswith("_count"):
            name = col.replace("last3_", "").replace("_count", "")
            candidate = f"{name}_count"
            if candidate in daily.columns:
                publisher_count_features.append(candidate)
        if col.startswith("last3_") and col.endswith("_avg_sentiment"):
            name = col.replace("last3_", "")
            if name in daily.columns:
                publisher_sentiment_features.append(name)

    for col in count_features + topic_features + publisher_count_features:
        if col in daily.columns:
            row[f"last3_{col}"] = last_3[col].sum()

    for col in sentiment_features + publisher_sentiment_features:
        if col in daily.columns:
            row[f"last3_{col}"] = last_3[col].mean()

    current_3_count = last_3["tweet_count"].sum()
    if len(daily) >= 6:
        prev_3_count = daily.iloc[-6:-3]["tweet_count"].sum()
        row["last3_tweet_change"] = current_3_count - prev_3_count
    else:
        row["last3_tweet_change"] = 0

    total_topic_count = sum(row.get(f"last3_{col}", 0) for col in topic_features)
    row["last3_total_topic_count"] = total_topic_count
    for col in topic_features:
        row[f"last3_{col}_ratio"] = (
            row.get(f"last3_{col}", 0) / total_topic_count
            if total_topic_count > 0 else 0
        )

    # ==============================
    # PRICE / MOMENTUM / LAG FEATURES
    # ==============================

    p0 = last_3["oil_price"].iloc[0]   # D-2
    p1 = last_3["oil_price"].iloc[1]   # D-1
    p2 = last_3["oil_price"].iloc[2]   # D  (most recent known)

    row["oil_price_d"]        = p2
    row["oil_price_d_minus1"] = p1
    row["oil_price_d_minus2"] = p0

    row["last3_oil_price_avg"]    = last_3["oil_price"].mean()
    row["last3_oil_price_min"]    = last_3["oil_price"].min()
    row["last3_oil_price_max"]    = last_3["oil_price"].max()
    row["last3_oil_price_std"]    = last_3["oil_price"].std() if len(last_3) > 1 else 0
    row["last3_oil_price_change"] = p2 - p0

    row["oil_momentum_1d"]   = p2 - p1
    row["oil_momentum_2d"]   = p1 - p0
    row["oil_pct_change_1d"] = (p2 - p1) / p1 if p1 != 0 else 0
    row["oil_pct_change_2d"] = (p1 - p0) / p0 if p0 != 0 else 0
    row["oil_pct_change_3d"] = (p2 - p0) / p0 if p0 != 0 else 0
    row["oil_acceleration"]  = row["oil_momentum_1d"] - row["oil_momentum_2d"]
    row["oil_range_3d"]      = last_3["oil_price"].max() - last_3["oil_price"].min()
    row["oil_price_vs_avg3"] = p2 - last_3["oil_price"].mean()

    row["oil_up_1d"]  = 1 if row["oil_momentum_1d"] > 0 else 0
    row["oil_up_2d"]  = 1 if row["oil_momentum_2d"] > 0 else 0
    row["oil_up_3d"]  = 1 if row["last3_oil_price_change"] > 0 else 0
    row["oil_streak"] = row["oil_up_1d"] + row["oil_up_2d"] + row["oil_up_3d"]

    # 7-day lookback
    if i >= 7:
        p_7d      = daily.iloc[i - 7]["oil_price"]
        rolling_7 = daily.iloc[i - 6:i + 1]["oil_price"].mean()
        row["oil_price_7d_ago"]   = p_7d
        row["oil_pct_change_7d"]  = (p2 - p_7d) / p_7d if p_7d != 0 else 0
        row["oil_rolling_avg_7d"] = rolling_7
        row["oil_price_vs_avg7"]  = p2 - rolling_7
    else:
        row["oil_price_7d_ago"]   = p2
        row["oil_pct_change_7d"]  = 0
        row["oil_rolling_avg_7d"] = last_3["oil_price"].mean()
        row["oil_price_vs_avg7"]  = 0

    # 14-day lookback
    if i >= 14:
        p_14d      = daily.iloc[i - 14]["oil_price"]
        rolling_14 = daily.iloc[i - 13:i + 1]["oil_price"].mean()
        row["oil_price_14d_ago"]   = p_14d
        row["oil_pct_change_14d"]  = (p2 - p_14d) / p_14d if p_14d != 0 else 0
        row["oil_rolling_avg_14d"] = rolling_14
        row["oil_price_vs_avg14"]  = p2 - rolling_14
    else:
        row["oil_price_14d_ago"]   = p2
        row["oil_pct_change_14d"]  = 0
        row["oil_rolling_avg_14d"] = last_3["oil_price"].mean()
        row["oil_price_vs_avg14"]  = 0

    # ==============================
    # EXTENDED TREND FEATURES
    # Must match Trainmodel.py.
    # ==============================

    if i >= 5:
        p_5d = daily.iloc[i - 5]["oil_price"]
        row["oil_pct_change_5d"]  = (p2 - p_5d) / p_5d if p_5d != 0 else 0
        row["oil_rolling_avg_5d"] = daily.iloc[i - 4:i + 1]["oil_price"].mean()
        row["oil_price_vs_avg5"]  = p2 - row["oil_rolling_avg_5d"]

        last_5_prices = daily.iloc[i - 4:i + 1]["oil_price"].values
        last_5_moves = [
            1 if last_5_prices[j] > last_5_prices[j - 1] else -1
            for j in range(1, len(last_5_prices))
        ]
        row["oil_streak_5d"] = sum(last_5_moves)
    else:
        row["oil_pct_change_5d"]  = 0
        row["oil_rolling_avg_5d"] = last_3["oil_price"].mean()
        row["oil_price_vs_avg5"]  = 0
        row["oil_streak_5d"]      = 0

    # Publisher tweet ratios — same feature definitions as training.
    total_tw = row.get("last3_tweet_count", 1) or 1
    row["idf_tweet_ratio"]      = row.get("last3_IDF_count", 0) / total_tw
    row["russia_tweet_ratio"]   = row.get("last3_mfa_russia_count", 0) / total_tw
    row["araghchi_tweet_ratio"] = row.get("last3_araghchi_count", 0) / total_tw

    # ==============================
    # FEATURE AMPLIFICATION
    # Must exactly match Trainmodel.py.
    # ==============================

    PUBLISHER_WEIGHT = 3.0
    for col in [
        "last3_IDF_count",
        "last3_mfa_russia_count",
        "last3_araghchi_count",
    ]:
        if col in row:
            row[col] = row[col] * PUBLISHER_WEIGHT

    SENTIMENT_WEIGHT = 3.0
    for col in [
        "last3_IDF_avg_sentiment",
        "last3_mfa_russia_avg_sentiment",
        "last3_araghchi_avg_sentiment",
    ]:
        if col in row:
            row[col] = row[col] * SENTIMENT_WEIGHT

    TREND_WEIGHT = 2.5
    for col in [
        "oil_streak",
        "oil_momentum_1d",
        "oil_momentum_2d",
        "oil_acceleration",
        "oil_pct_change_1d",
        "oil_pct_change_3d",
        "oil_pct_change_7d",
        "oil_pct_change_14d",
        "oil_price_vs_avg3",
        "oil_price_vs_avg7",
        "oil_price_vs_avg14",
    ]:
        if col in row:
            row[col] = row[col] * TREND_WEIGHT

    DIR_WEIGHT = 2.0
    for col in ["oil_up_1d", "oil_up_2d", "oil_up_3d"]:
        if col in row:
            row[col] = row[col] * DIR_WEIGHT

    last3_text = " ".join(last_3["daily_text"].astype(str))

    return row, last3_text, last_3


# ==============================
# MODEL INPUT
# ==============================

def build_model_input(row, last3_text, tfidf, feature_columns):
    numeric_df = pd.DataFrame([row]).fillna(0)

    if tfidf is not None:
        text_features = tfidf.transform([last3_text]).toarray()
        text_feature_names = [
            f"word_{w}" for w in tfidf.get_feature_names_out()
        ]
        text_df = pd.DataFrame(
            text_features,
            columns=text_feature_names
        )

        full_df = pd.concat(
            [
                numeric_df.reset_index(drop=True),
                text_df.reset_index(drop=True),
            ],
            axis=1
        )

        print(
            f"TF-IDF enabled: {len(text_feature_names)} text features."
        )

    else:
        # The selected training run may have been trained without text
        # features. In that case tfidf.pkl intentionally contains None.
        full_df = numeric_df.reset_index(drop=True)
        print("TF-IDF not used by trained model; using numeric features only.")

    # Force the exact columns and exact order used during training.
    X_input = full_df.reindex(
        columns=feature_columns,
        fill_value=0
    )

    print(
        f"Built prediction features: {X_input.shape[1]} "
        f"(expected {len(feature_columns)})"
    )

    return X_input


# ==============================
# UPDATE OLD PREDICTIONS WITH ACTUAL PRICES
# ==============================

def update_old_predictions_with_actual_prices(daily, bin_edges):
    client     = MongoClient(MONGO_URI)
    db         = client[DB_NAME]
    collection = db[PREDICTIONS_COLLECTION]

    daily_lookup = {
        str(row["date"].date()): float(row["oil_price"])
        for _, row in daily.iterrows()
    }

    pending = list(collection.find({"actual_price": None}))

    print("\n==============================")
    print("UPDATING OLD PREDICTIONS")
    print("==============================")
    print(f"Pending predictions: {len(pending)}")

    updated_count = 0

    for prediction in pending:
        target_date = prediction.get("target_date")

        if target_date not in daily_lookup:
            print(f"No actual price yet for {target_date}")
            continue

        actual_price = daily_lookup[target_date]
        actual_bin, actual_range = get_bin_for_price(actual_price, bin_edges)
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
                    "actual_bin":   actual_bin,
                    "actual_range": actual_range,
                    "is_correct":   is_correct,
                    "updated_at":   datetime.utcnow()
                }
            }
        )

        updated_count += 1
        print(
            f"Updated {target_date}: "
            f"actual_price={actual_price:.2f}, "
            f"actual_range={actual_range}, "
            f"correct={is_correct}"
        )

    print(f"Old predictions updated: {updated_count}")


# ==============================
# SAVE NEW PREDICTION
# ==============================

def save_prediction_to_mongo(prediction_doc):
    client     = MongoClient(MONGO_URI)
    db         = client[DB_NAME]
    collection = db[PREDICTIONS_COLLECTION]

    collection.update_one(
        {"target_date": prediction_doc["target_date"]},
        {
            "$set": prediction_doc,
            "$setOnInsert": {"first_created_at": datetime.utcnow()}
        },
        upsert=True
    )

    print("\nPrediction saved to MongoDB.")
    print(prediction_doc)


# ==============================
# MAIN
# ==============================

def main():
    # CHANGED: download this week's model from Hugging Face Hub instead of
    # (optionally) retraining locally.
    download_artifacts()

    print("\n==============================")
    print("Loading model artifacts")
    print("==============================")

    model           = joblib.load(MODEL_FILE)
    tfidf           = joblib.load(TFIDF_FILE)
    feature_columns = joblib.load(FEATURE_COLUMNS_FILE)
    bin_edges       = joblib.load(BIN_EDGES_FILE)   # numpy array

    print("Model loaded:", MODEL_FILE)
    print("Expected feature count:", len(feature_columns))
    print("TF-IDF artifact:", "enabled" if tfidf is not None else "None (numeric-only model)")
    print("Bin edges:", bin_edges)

    print("Loading training data from MongoDB...")
    client          = MongoClient(MONGO_URI)
    records         = list(client[DB_NAME][TRAINING_COLLECTION].find({}, {"_id": 0}))
    print(f"Loaded {len(records)} documents from MongoDB.")
    df              = pd.DataFrame(records)
    daily           = build_daily_features(df, feature_columns)

    # Step 1: fill in actual prices for any past predictions that were pending
    update_old_predictions_with_actual_prices(daily, bin_edges)

    # Step 2: predict the day after the latest available oil data
    row, last3_text, last_3 = build_prediction_row(daily, feature_columns)

    X_input = build_model_input(
        row             = row,
        last3_text      = last3_text,
        tfidf           = tfidf,
        feature_columns = feature_columns
    )

    print("\nPrediction input shape:", X_input.shape)

    if X_input.shape[1] != len(feature_columns):
        raise ValueError(
            f"Feature mismatch: X_input has {X_input.shape[1]} features, "
            f"but expected {len(feature_columns)}."
        )

    predicted_bin   = int(model.predict(X_input.values)[0])
    predicted_range = bin_label(predicted_bin, bin_edges)

    latest_date = daily["date"].max().date()

    # Training predicts the next AVAILABLE oil-price row, not necessarily
    # the next calendar day. At minimum, skip weekends so Friday predictions
    # target Monday rather than Saturday.
    target_date = (
        pd.Timestamp(latest_date) + BDay(1)
    ).date()

    prediction_doc = {
        "prediction_date":  str(datetime.today().date()),
        "target_date":      str(target_date),
        "latest_data_date": str(latest_date),
        "model_file":       "oil_model.pkl",

        "predicted_bin":   predicted_bin,
        "predicted_range": predicted_range,

        "actual_price": None,
        "actual_bin":   None,
        "actual_range": None,
        "is_correct":   None,

        "last3_dates": [str(d.date()) for d in last_3["date"]],
        "created_at":  datetime.utcnow()
    }

    print("\n==============================")
    print("NEXT OIL DATE PREDICTION")
    print("==============================")
    print("Latest data date:", latest_date)
    print("Target date:     ", target_date)
    print("Predicted range: ", predicted_range)

    save_prediction_to_mongo(prediction_doc)


if __name__ == "__main__":
    main()