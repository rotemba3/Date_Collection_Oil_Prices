import os
import pandas as pd

# ==============================
# PATHS
# ==============================

# CHANGED: relative to this file's location instead of a hardcoded Windows
# path, so this works unchanged on the GitHub Actions runner. Keep this
# file in the same folder as main.py so the relative paths below still
# line up with what main.py writes.
base_dir = os.path.dirname(os.path.abspath(__file__))

timelines_dir        = os.path.join(base_dir, "Data", "Users_Timelines")
combined_tweets_file = os.path.join(base_dir, "combined_tweets.csv")
oil_file             = os.path.join(base_dir, "_WTI - חוזים עתידיים על נפט גולמי - נתונים היסטוריים.csv")
output_file          = os.path.join(base_dir, "tweets_oil_gas_combined.csv")


# ==============================
# HELPERS
# ==============================

def normalize_change_percent(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.startswith("+"):
        s = s[1:]
    return s


# ==============================
# LOAD EXISTING combined_tweets.csv (if any)
# ==============================

if os.path.exists(combined_tweets_file):
    existing_tweets = pd.read_csv(combined_tweets_file, encoding="utf-8-sig")
    print(f"Loaded existing combined_tweets.csv: {len(existing_tweets)} rows")
else:
    existing_tweets = pd.DataFrame(columns=["created_at", "text", "publisher"])
    print("No existing combined_tweets.csv — starting fresh.")


# ==============================
# LOAD NEW TWEETS FROM Users_Timelines
# ==============================

new_tweets = []

for filename in os.listdir(timelines_dir):
    if not filename.endswith(".csv"):
        continue

    file_path = os.path.join(timelines_dir, filename)
    username  = filename.replace(".csv", "")

    try:
        if os.path.getsize(file_path) == 0:
            print(f"Skipping empty file: {filename}")
            continue

        df = pd.read_csv(file_path, encoding="utf-8-sig")

    except pd.errors.EmptyDataError:
        print(f"Skipping empty CSV: {filename}")
        continue

    if df.empty:
        print(f"Skipping empty dataframe: {filename}")
        continue

    if "created_at" not in df.columns or "text" not in df.columns:
        print(f"Skipping invalid file (missing columns): {filename}")
        continue

    df = df[["created_at", "text"]].copy()
    df["publisher"] = username
    df = df.dropna(subset=["created_at", "text"])
    new_tweets.append(df)

if new_tweets:
    new_tweets_df = pd.concat(new_tweets, ignore_index=True)
    print(f"Scraped tweets this run: {len(new_tweets_df)}")
else:
    new_tweets_df = pd.DataFrame(columns=["created_at", "text", "publisher"])
    print("No new tweets scraped this run.")


# ==============================
# MERGE OLD + NEW TWEETS, DEDUPLICATE
# ==============================

combined_tweets = pd.concat(
    [existing_tweets, new_tweets_df],
    ignore_index=True
)

before_dedup = len(combined_tweets)

combined_tweets = combined_tweets.drop_duplicates(
    subset=["created_at", "text", "publisher"]
)

print(f"Deduplication: {before_dedup} → {len(combined_tweets)} rows")

combined_tweets.to_csv(combined_tweets_file, index=False, encoding="utf-8-sig")
print(f"Saved combined_tweets.csv: {len(combined_tweets)} total rows")


# ==============================
# PARSE DATE FROM combined_tweets
# ==============================

tweets = combined_tweets[["created_at", "text", "publisher"]].copy()

tweets["date"] = pd.to_datetime(
    tweets["created_at"],
    errors="coerce",
    utc=True
).dt.strftime("%Y-%m-%d")

tweets = tweets.dropna(subset=["date"])
tweets = tweets[["date", "text", "publisher"]]


# ==============================
# LOAD EXISTING output CSV (tweets_oil_gas_combined.csv)
# so we never lose historical rows even if oil CSV only has recent data
# ==============================

if os.path.exists(output_file):
    existing_output = pd.read_csv(output_file, encoding="utf-8-sig")
    print(f"Loaded existing tweets_oil_gas_combined.csv: {len(existing_output)} rows")
else:
    existing_output = pd.DataFrame()
    print("No existing tweets_oil_gas_combined.csv — will create fresh.")


# ==============================
# LOAD OIL CSV
# ==============================

oil = pd.read_csv(oil_file, encoding="utf-8-sig")

oil = oil.rename(columns={
    "תאריך":  "date",
    "שער":    "oil_price",
    "פתיחה":  "oil_open",
    "גבוה":   "oil_high",
    "נמוך":   "oil_low",
    "נפח":    "oil_volume",
    "שינוי %": "oil_change_percent",
    "שינוי":  "oil_change_percent"
})

needed_oil_cols = [
    "date", "oil_price", "oil_open", "oil_high",
    "oil_low", "oil_volume", "oil_change_percent"
]

# Keep only columns that actually exist in this CSV
oil = oil[[c for c in needed_oil_cols if c in oil.columns]].copy()

oil["date"] = pd.to_datetime(
    oil["date"],
    dayfirst=True,
    errors="coerce"
).dt.strftime("%Y-%m-%d")

oil = oil.dropna(subset=["date"])
oil["oil_change_percent"] = oil["oil_change_percent"].apply(normalize_change_percent)
oil = oil.drop_duplicates(subset=["date"])
oil = oil.sort_values("date")

print(f"Oil CSV date range: {oil['date'].min()} → {oil['date'].max()}")


# ==============================
# BUILD NEW ROWS FROM TWEETS + OIL
# ==============================

tweet_rows = tweets.merge(oil, on="date", how="left")

dates_with_tweets = set(tweets["date"])
oil_no_tweet = oil[~oil["date"].isin(dates_with_tweets)].copy()
oil_no_tweet["text"]      = "EMPTY"
oil_no_tweet["publisher"] = "EMPTY"

new_output = pd.concat([tweet_rows, oil_no_tweet], ignore_index=True)

output_cols = [
    "date", "text", "publisher",
    "oil_price", "oil_open", "oil_high",
    "oil_low", "oil_volume", "oil_change_percent"
]

# Only keep columns that exist
new_output = new_output[[c for c in output_cols if c in new_output.columns]]


# ==============================
# MERGE WITH EXISTING OUTPUT — keep all historical rows
# New rows overwrite existing rows for the same (date, publisher, text) key
# ==============================

if not existing_output.empty:
    combined_output = pd.concat(
        [existing_output, new_output],
        ignore_index=True
    )
    # Deduplicate: prefer the newer row (tail) for same date+publisher+text
    combined_output = combined_output.drop_duplicates(
        subset=["date", "text", "publisher"],
        keep="last"
    )
else:
    combined_output = new_output

combined_output = combined_output.sort_values(["date", "publisher", "text"])


# ==============================
# SAVE
# ==============================

combined_output.to_csv(output_file, index=False, encoding="utf-8-sig")

print(f"\nSaved tweets_oil_gas_combined.csv")
print(f"Total rows: {len(combined_output)}")
print(f"Date range: {combined_output['date'].min()} → {combined_output['date'].max()}")
print(f"Unique dates: {combined_output['date'].nunique()}")

print("\nSample (last 5 rows):")
print(combined_output.tail(5).to_string(index=False))