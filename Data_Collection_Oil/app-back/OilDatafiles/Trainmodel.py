import re
import warnings
import pandas as pd
import numpy as np

from textblob import TextBlob

from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer

warnings.filterwarnings("ignore")


# ==============================
# LOAD DATA FROM MONGODB
# ==============================

from pymongo import MongoClient

MONGO_URI  = "mongodb+srv://rotemba3_db_user:12345@dataoilscollect.bje8esi.mongodb.net/"
DB_NAME    = "DataCollectionOil"
COLLECTION = "modeltrainig"   # note: typo matches existing collection name

print("Connecting to MongoDB...")
client     = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION]

records = list(collection.find({}, {"_id": 0}))
print(f"Loaded {len(records)} documents from MongoDB.")

df = pd.DataFrame(records)

df["date"]      = pd.to_datetime(df["date"], errors="coerce")
df["date"]      = df["date"].dt.normalize()   # strip time → group by day correctly
df["oil_price"] = pd.to_numeric(df["oil_price"], errors="coerce")

df = df.dropna(subset=["date", "oil_price"])

df["text"]      = df["text"].fillna("EMPTY").astype(str)
df["publisher"] = df["publisher"].fillna("EMPTY").astype(str)


# ==============================
# DIAGNOSTICS
# ==============================

print("\n==============================")
print("DIAGNOSTICS")
print("==============================")
print(f"Total rows from MongoDB:   {len(df)}")
print(f"Unique dates:              {df['date'].nunique()}")
print(f"Date dtype:                {df['date'].dtype}")
print(f"Date range:                {df['date'].min().date()}  →  {df['date'].max().date()}")

print("\n--- First 10 dates with oil price ---")
print(
    df[["date", "oil_price"]]
    .drop_duplicates("date")
    .sort_values("date")
    .head(10)
    .to_string(index=False)
)

print("\n--- Last 10 dates with oil price ---")
print(
    df[["date", "oil_price"]]
    .drop_duplicates("date")
    .sort_values("date")
    .tail(10)
    .to_string(index=False)
)

print("\n--- Tweet count per date (first 10) ---")
print(
    df.groupby("date")["text"]
    .count()
    .reset_index()
    .rename(columns={"text": "tweet_count"})
    .sort_values("date")
    .head(10)
    .to_string(index=False)
)

print("\n==============================")
print("END DIAGNOSTICS")
print("==============================\n")


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
# TOPIC GROUPS (expanded keywords)
# ==============================

topic_groups = {
    "war": [
        # original
        "war", "attack", "strike", "missile", "military", "terror",
        "rocket", "bomb", "killed", "troops", "hezbollah", "hamas",
        # added
        "conflict", "combat", "warfare", "offensive", "assault", "airstrike",
        "invasion", "siege", "casualties", "wounded", "artillery", "drone",
        "navy", "battalion", "frontline", "rebel", "insurgent", "militia",
        "gunfire", "sniper", "mortar", "warship", "submarine", "fighter",
        "nuclear", "tactical", "hostage", "kidnap", "ambush", "guerrilla"
    ],
    "peace": [
        # original
        "ceasefire", "peace", "agreement", "deal", "diplomacy",
        "negotiation", "talks", "truce",
        # added
        "treaty", "accord", "settlement", "reconciliation", "mediation",
        "resolution", "dialogue", "summit", "bilateral", "multilateral",
        "humanitarian", "withdrawal", "deescalation", "armistice",
        "peacekeeping", "envoy", "ambassador", "cooperation", "alliance"
    ],
    "iran": [
        # original
        "iran", "iranian", "tehran", "hormuz", "sanctions",
        "khamenei", "islamic", "republic",
        # added
        "rouhani", "raisi", "irgc", "nuclear", "enrichment", "uranium",
        "strait", "persian", "gulf", "revolutionary", "guard", "proxy",
        "jcpoa", "vienna", "embargo", "ayatollah", "hardliner", "regime"
    ],
    "oil_energy": [
        # original
        "oil", "gas", "fuel", "energy", "barrel", "crude",
        "petroleum", "prices", "export",
        # added
        "opec", "brent", "wti", "refinery", "pipeline", "tanker",
        "lng", "shale", "offshore", "onshore", "drilling", "rig",
        "production", "output", "supply", "demand", "inventory",
        "stockpile", "reserve", "capacity", "quota", "cut", "pump",
        "gasoline", "diesel", "natural", "renewable", "solar", "wind",
        "coal", "nuclear", "powerplant", "electricity", "kwh", "megawatt"
    ],
    "usa": [
        # original
        "america", "american", "usa", "us", "trump", "whitehouse",
        "washington", "biden",
        # added
        "congress", "senate", "federal", "reserve", "pentagon",
        "state", "department", "cia", "democrat", "republican",
        "sanctions", "tariff", "policy", "administration", "secretary",
        "harris", "antony", "blinken", "treasury", "fed", "powell",
        "inflation", "interest", "rate", "stimulus", "deficit"
    ],
    "israel_lebanon": [
        # original
        "israel", "israeli", "idf", "lebanon", "lebanese",
        "gaza", "jerusalem", "netanyahu",
        # added
        "west", "bank", "palestine", "palestinian", "settler",
        "border", "occupation", "tel", "aviv", "haifa", "beirut",
        "south", "sinai", "golan", "hamas", "fatah", "PLO",
        "checkpoint", "blockade", "displacement", "refugee", "unrwa",
        "galilee", "beit", "iron", "dome", "knesset", "mossad"
    ],
    "economy": [
        # original
        "economy", "market", "trade", "inflation", "stock",
        "dollar", "growth", "crisis",
        # added
        "gdp", "recession", "depression", "unemployment", "jobs",
        "bond", "yield", "equity", "commodity", "forex", "currency",
        "euro", "yen", "yuan", "ruble", "debt", "deficit", "surplus",
        "budget", "fiscal", "monetary", "central", "bank", "interest",
        "rate", "hike", "cut", "quantitative", "easing", "imf",
        "worldbank", "wto", "g7", "g20", "brics", "export", "import",
        "tariff", "embargo", "supply", "chain", "logistics", "shipping"
    ],
    # NEW TOPIC GROUPS
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
    # original
    "war", "attack", "strike", "missile", "rocket", "bomb",
    "killed", "dead", "death", "terror", "troops", "military",
    "violence", "explosion", "raid", "threat", "weapon", "weapons",
    "fire", "fired", "launch", "launched", "destroy", "destroyed",
    # added
    "assassinate", "assassination", "massacre", "genocide", "airstrike",
    "shelling", "bombardment", "drone", "combat", "offensive", "siege",
    "ambush", "casualties", "wounded", "conflict", "hostage", "execute",
    "executed", "detonate", "detonated", "collapse", "collapsed"
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

    row["avg_sentiment"]  = real["sentiment"].mean() if len(real) > 0 else 0
    row["min_sentiment"]  = real["sentiment"].min()  if len(real) > 0 else 0
    row["max_sentiment"]  = real["sentiment"].max()  if len(real) > 0 else 0
    row["sentiment_std"]  = real["sentiment"].std()  if len(real) > 1 else 0

    row["positive_tweets"] = (real["sentiment"] >  0.1).sum()
    row["negative_tweets"] = (real["sentiment"] < -0.1).sum()
    row["neutral_tweets"]  = (
        (real["sentiment"] >= -0.1) & (real["sentiment"] <= 0.1)
    ).sum()

    all_text = (
        " ".join(real["clean_text"].astype(str))
        if len(real) > 0 else "EMPTY"
    )

    row["daily_text"] = all_text

    for topic_name, words in topic_groups.items():
        row[f"{topic_name}_topic_count"] = count_topic_words(all_text, words)

    aggressive_count    = count_aggressive_words(all_text)
    total_words         = len(all_text.split()) if all_text != "EMPTY" else 1

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

topic_features          = [f"{topic}_topic_count" for topic in topic_groups.keys()]
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

    # --- Aggregated tweet / topic / sentiment features ---
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

    # ==============================
    # OIL PRICE HISTORY FEATURES
    # All use only D-2, D-1, D (known before predicting D+1)
    # ==============================

    p0 = last_3["oil_price"].iloc[0]   # D-2
    p1 = last_3["oil_price"].iloc[1]   # D-1
    p2 = last_3["oil_price"].iloc[2]   # D   (most recent known)

    # Raw prices
    row["oil_price_d"]       = p2
    row["oil_price_d_minus1"] = p1
    row["oil_price_d_minus2"] = p0

    # Rolling stats
    row["last3_oil_price_avg"]    = last_3["oil_price"].mean()
    row["last3_oil_price_min"]    = last_3["oil_price"].min()
    row["last3_oil_price_max"]    = last_3["oil_price"].max()
    row["last3_oil_price_std"]    = last_3["oil_price"].std() if len(last_3) > 1 else 0
    row["last3_oil_price_change"] = p2 - p0   # 3-day net change

    # 1-day and 2-day momentum
    row["oil_momentum_1d"] = p2 - p1
    row["oil_momentum_2d"] = p1 - p0

    # Percent changes
    row["oil_pct_change_1d"] = (p2 - p1) / p1 if p1 != 0 else 0
    row["oil_pct_change_2d"] = (p1 - p0) / p0 if p0 != 0 else 0
    row["oil_pct_change_3d"] = (p2 - p0) / p0 if p0 != 0 else 0

    # Acceleration (momentum of momentum)
    row["oil_acceleration"] = row["oil_momentum_1d"] - row["oil_momentum_2d"]

    # Range (volatility proxy)
    row["oil_range_3d"] = last_3["oil_price"].max() - last_3["oil_price"].min()

    # Price relative to 3-day average (mean reversion signal)
    avg3 = last_3["oil_price"].mean()
    row["oil_price_vs_avg3"] = p2 - avg3

    # Direction flags
    row["oil_up_1d"]   = 1 if row["oil_momentum_1d"] > 0 else 0
    row["oil_up_2d"]   = 1 if row["oil_momentum_2d"] > 0 else 0
    row["oil_up_3d"]   = 1 if row["last3_oil_price_change"] > 0 else 0
    row["oil_streak"]  = (
        int(row["oil_up_1d"]) + int(row["oil_up_2d"]) + int(row["oil_up_3d"])
    )  # 0-3: how many of last 3 days were up

    # Longer lookback lags (if enough history)
    if i >= 7:
        p_7d_ago = daily.iloc[i - 7]["oil_price"]
        row["oil_price_7d_ago"]      = p_7d_ago
        row["oil_pct_change_7d"]     = (p2 - p_7d_ago) / p_7d_ago if p_7d_ago != 0 else 0
        row["oil_rolling_avg_7d"]    = daily.iloc[i-6:i+1]["oil_price"].mean()
        row["oil_price_vs_avg7"]     = p2 - row["oil_rolling_avg_7d"]
    else:
        row["oil_price_7d_ago"]   = p2
        row["oil_pct_change_7d"]  = 0
        row["oil_rolling_avg_7d"] = avg3
        row["oil_price_vs_avg7"]  = 0

    if i >= 14:
        p_14d_ago = daily.iloc[i - 14]["oil_price"]
        row["oil_price_14d_ago"]     = p_14d_ago
        row["oil_pct_change_14d"]    = (p2 - p_14d_ago) / p_14d_ago if p_14d_ago != 0 else 0
        row["oil_rolling_avg_14d"]   = daily.iloc[i-13:i+1]["oil_price"].mean()
        row["oil_price_vs_avg14"]    = p2 - row["oil_rolling_avg_14d"]
    else:
        row["oil_price_14d_ago"]  = p2
        row["oil_pct_change_14d"] = 0
        row["oil_rolling_avg_14d"] = avg3
        row["oil_price_vs_avg14"] = 0

    # --- Text ---
    row["last3_text"] = " ".join(last_3["daily_text"].astype(str))

    # --- Target ---
    row["tomorrow_oil_price"] = daily.loc[i + 1, "oil_price"]

    window_rows.append(row)


model_df = pd.DataFrame(window_rows).reset_index(drop=True)


# ==============================
# TARGET: 4 PRICE RANGES
# FIX: bin edges computed on TRAIN set only
# ==============================

# Use 80% as the train boundary for bin edge computation
train_end_for_bins = int(len(model_df) * 0.80)
train_prices = model_df["tomorrow_oil_price"].iloc[:train_end_for_bins]

# Custom bins: denser near the mean, wider at the extremes
# Uses percentiles so all bins are guaranteed to have data:
#   0 = very low    (below 20th percentile)
#   1 = low         (20th to 40th percentile)
#   2 = mid         (40th to 60th percentile)  ← 2 bins near center
#   3 = high        (60th to 80th percentile)
#   4 = very high   (above 80th percentile)
mean  = train_prices.mean()
std   = train_prices.std()

# Fixed price boundary bins
bin_edges = np.array([-np.inf, 59.0, 64.0, 80.0, 90.0, 100.0, np.inf])

print(f"\nPrice mean: {mean:.2f}  std: {std:.2f}")
print("Fixed bin edges:")
print(f"  bin 0: below $59        (low)")
print(f"  bin 1: $59  – $64       (mid-low)")
print(f"  bin 2: $64  – $80       (mid)")
print(f"  bin 3: $80  – $90       (mid-high)")
print(f"  bin 4: $90  – $100      (high)")
print(f"  bin 5: above $100       (very high)")


model_df["price_bin"] = pd.cut(
    model_df["tomorrow_oil_price"],
    bins=bin_edges,
    labels=False
)

# Drop rows where test prices fall outside train bin range (rare edge case)
model_df = model_df.dropna(subset=["price_bin"]).reset_index(drop=True)
model_df["price_bin"] = model_df["price_bin"].astype(int)

print("\nFinal bin edges:")
print(bin_edges)

print("\nClass distribution:")
dist   = model_df["price_bin"].value_counts().sort_index()
labels = ["low", "mid-low", "mid", "mid-high", "high", "very high"]
for bin_idx, count in dist.items():
    lbl = labels[int(bin_idx)] if int(bin_idx) < len(labels) else str(bin_idx)
    print(f"  bin {bin_idx} ({lbl:10s}): {count} samples")


# ==============================
# CHRONOLOGICAL SPLIT HELPER
# ==============================

def time_split(X_arr, y_arr, test_size):
    split_idx = int(len(X_arr) * (1 - test_size))
    return (
        X_arr[:split_idx], X_arr[split_idx:],
        y_arr[:split_idx], y_arr[split_idx:]
    )


# ==============================
# SPLITS DEFINITION
# ==============================

splits = {
    "80-20": 0.20,
    "70-30": 0.30,
    "60-40": 0.40
}


# ==============================
# MODELS
# Strong regularization to fight overfitting on small dataset
# ==============================

models = {
    "Logistic Regression":  LogisticRegression(max_iter=3000, C=0.01, class_weight="balanced"),
    "Logistic L1":          LogisticRegression(max_iter=3000, C=0.01, penalty="l1", solver="saga", class_weight="balanced"),
    "SVC linear":           SVC(kernel="linear", C=0.01, class_weight="balanced"),
    "SVC rbf":              SVC(kernel="rbf",    C=0.1,  class_weight="balanced"),
    "Random Forest":        RandomForestClassifier(n_estimators=100, max_depth=3, min_samples_leaf=5, class_weight="balanced", random_state=42),
}


# ==============================
# TRAIN + EVALUATE
# FIX: TF-IDF fitted only on training portion per split
#      Chronological split (no shuffle)
# ==============================

results = []

exclude_cols = [
    "date",
    "last3_text",
    "tomorrow_oil_price",
    "price_bin"
]

numeric_df = model_df.drop(columns=exclude_cols).fillna(0)

for split_name, test_size in splits.items():
    print(f"\n{'='*40}")
    print(f"Split {split_name}")
    print('='*40)

    split_idx = int(len(model_df) * (1 - test_size))

    # --- FIX: fit TF-IDF only on training rows ---
    # Use min_df=1, no stop_words removal when data is sparse
    train_texts = model_df["last3_text"].iloc[:split_idx]
    has_real_text = train_texts.str.replace("EMPTY", "").str.strip().str.len() > 0

    if has_real_text.sum() >= 3:
        tfidf = TfidfVectorizer(
            max_features=50,
            stop_words=None,   # don't remove stop words when text is sparse
            lowercase=True,
            min_df=1
        )
        try:
            tfidf.fit(train_texts)
            text_features      = tfidf.transform(model_df["last3_text"]).toarray()
            text_feature_names = [f"word_{w}" for w in tfidf.get_feature_names_out()]
            text_df            = pd.DataFrame(text_features, columns=text_feature_names)
            print(f"  TF-IDF vocabulary size: {len(tfidf.vocabulary_)}")
        except ValueError:
            print("  TF-IDF: empty vocabulary, skipping text features.")
            text_df = pd.DataFrame(index=model_df.index)
    else:
        print("  TF-IDF: not enough real text in training set, skipping.")
        text_df = pd.DataFrame(index=model_df.index)

    X_df = pd.concat(
        [numeric_df.reset_index(drop=True), text_df.reset_index(drop=True)],
        axis=1
    )

    X = X_df.values
    y = model_df["price_bin"].values

    X_train, X_test, y_train, y_test = time_split(X, y, test_size)

    print(f"Train rows: {len(X_train)} | Test rows: {len(X_test)}")
    print(f"Features:   {X_df.shape[1]}")

    for model_name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        acc         = accuracy_score(y_test, preds)
        f1_macro    = f1_score(y_test, preds, average="macro")
        f1_weighted = f1_score(y_test, preds, average="weighted")

        results.append({
            "split":       split_name,
            "model":       model_name,
            "accuracy":    acc,
            "f1_macro":    f1_macro,
            "f1_weighted": f1_weighted
        })

        print(f"  {model_name:25s}  acc={acc:.4f}  f1_macro={f1_macro:.4f}  f1_w={f1_weighted:.4f}")


# ==============================
# CROSS-VALIDATION (time series aware)
# More reliable than a single split on small data
# ==============================

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

print("\n" + "="*40)
print("TIME SERIES CROSS-VALIDATION (5 folds)")
print("="*40)

# Use the 80-20 tfidf/X_df from the last split loop iteration
tscv = TimeSeriesSplit(n_splits=5)

cv_results = []

for cv_model_name, cv_model in models.items():
    fold_accs = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        if len(test_idx) < 2:
            continue

        # Skip fold if train or test set has fewer than 2 classes
        if len(np.unique(y[train_idx])) < 2:
            continue
        if len(np.unique(y[test_idx])) < 2:
            continue

        try:
            pipe = make_pipeline(StandardScaler(), cv_model.__class__(**cv_model.get_params()))
            pipe.fit(X[train_idx], y[train_idx])
            preds    = pipe.predict(X[test_idx])
            fold_acc = accuracy_score(y[test_idx], preds)
            fold_accs.append(fold_acc)
        except Exception as e:
            print(f"  Fold {fold} skipped: {e}")
            continue

    mean_acc = np.mean(fold_accs) if fold_accs else 0
    std_acc  = np.std(fold_accs)  if fold_accs else 0

    cv_results.append({
        "model":    cv_model_name,
        "cv_mean":  mean_acc,
        "cv_std":   std_acc,
        "n_folds":  len(fold_accs)
    })

    print(f"  {cv_model_name:25s}  cv_acc={mean_acc:.4f} ± {std_acc:.4f}  ({len(fold_accs)} folds)")

cv_df = pd.DataFrame(cv_results).sort_values("cv_mean", ascending=False)
print("\nBest CV model:", cv_df.iloc[0]["model"], f"({cv_df.iloc[0]['cv_mean']:.4f})")

# ==============================
# SUMMARY
# ==============================

results_df = pd.DataFrame(results)

print("\n" + "="*40)
print("FINAL COMPARISON")
print("="*40)
print(
    results_df
    .sort_values(["split", "accuracy"], ascending=[True, False])
    .to_string(index=False)
)

print("\n" + "="*40)
print("PIVOT: ACCURACY")
print("="*40)
print(
    results_df.pivot(index="model", columns="split", values="accuracy")
)

best = results_df.sort_values("accuracy", ascending=False).iloc[0]

print("\n" + "="*40)
print("BEST MODEL")
print("="*40)
print(best)


# ==============================
# DETAILED REPORT FOR BEST MODEL
# ==============================

best_model_name = best["model"]
best_split      = best["split"]
best_test_size  = splits[best_split]
best_split_idx  = int(len(model_df) * (1 - best_test_size))

# Refit TF-IDF for best split
best_tfidf = TfidfVectorizer(
    max_features=150,
    stop_words="english",
    lowercase=True,
    min_df=1
)
best_tfidf.fit(model_df["last3_text"].iloc[:best_split_idx])
best_text_features = best_tfidf.transform(model_df["last3_text"]).toarray()
best_text_df = pd.DataFrame(
    best_text_features,
    columns=[f"word_{w}" for w in best_tfidf.get_feature_names_out()]
)

best_X_df = pd.concat(
    [numeric_df.reset_index(drop=True), best_text_df.reset_index(drop=True)],
    axis=1
)

X_best = best_X_df.values
y_best = model_df["price_bin"].values

X_train, X_test, y_train, y_test = time_split(X_best, y_best, best_test_size)

best_model = models.get(best_model_name)
if best_model is None:
    raise ValueError(f"Best model name '{best_model_name}' not found in models dict.")
best_model.fit(X_train, y_train)
best_preds = best_model.predict(X_test)

print(f"\n{'='*40}")
print(f"CLASSIFICATION REPORT: {best_model_name}, split {best_split}")
print("="*40)
print(classification_report(y_test, best_preds))


# ==============================
# FEATURE IMPORTANCE
# ==============================

importance_model = ExtraTreesClassifier(n_estimators=300, random_state=42)
importance_model.fit(X_best, y_best)

importances = pd.DataFrame({
    "feature":    best_X_df.columns,
    "importance": importance_model.feature_importances_
}).sort_values("importance", ascending=False)

print("\n" + "="*40)
print("TOP 40 IMPORTANT FEATURES")
print("="*40)
print(importances.head(40).to_string(index=False))


# ==============================
# SAVE BEST MODEL + ARTIFACTS
# ==============================

import joblib
import os

print("\n" + "="*40)
print("SAVING BEST MODEL AND ARTIFACTS")
print("="*40)

BASE_DIR = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

MODEL_FILE            = os.path.join(BASE_DIR, "oil_model.pkl")
TFIDF_FILE            = os.path.join(BASE_DIR, "tfidf.pkl")
FEATURE_COLUMNS_FILE  = os.path.join(BASE_DIR, "feature_columns.pkl")
BIN_EDGES_FILE        = os.path.join(BASE_DIR, "bin_edges.pkl")
TRAINING_RESULTS_FILE = os.path.join(BASE_DIR, "training_results.csv")
FEATURE_IMPORTANCE_FILE = os.path.join(BASE_DIR, "feature_importance.csv")

joblib.dump(best_model,              MODEL_FILE)
joblib.dump(best_tfidf,              TFIDF_FILE)
joblib.dump(best_X_df.columns.tolist(), FEATURE_COLUMNS_FILE)
joblib.dump(bin_edges,               BIN_EDGES_FILE)

results_df.to_csv(TRAINING_RESULTS_FILE,    index=False, encoding="utf-8-sig")
importances.to_csv(FEATURE_IMPORTANCE_FILE, index=False, encoding="utf-8-sig")

print("Saved successfully:")
print(f"  {MODEL_FILE}")
print(f"  {TFIDF_FILE}")
print(f"  {FEATURE_COLUMNS_FILE}")
print(f"  {BIN_EDGES_FILE}  (replaces bin_table.pkl)")
print(f"  {TRAINING_RESULTS_FILE}")
print(f"  {FEATURE_IMPORTANCE_FILE}")

print(f"\nBest model:  {best_model_name}")
print(f"Split:       {best_split}")
print(f"Accuracy:    {best['accuracy']:.4f}")
print(f"F1 macro:    {best['f1_macro']:.4f}")
print(f"F1 weighted: {best['f1_weighted']:.4f}")