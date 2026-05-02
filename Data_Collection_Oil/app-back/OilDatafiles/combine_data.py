import os
import pandas as pd

# ==============================
# PATHS
# ==============================

base_dir = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

timelines_dir = os.path.join(base_dir, "Data", "Users_Timelines")

combined_tweets_file = os.path.join(base_dir, "combined_tweets.csv")

oil_file = os.path.join(
    base_dir,
    "_WTI - חוזים עתידיים על נפט גולמי - נתונים היסטוריים.csv"
)

output_file = os.path.join(base_dir, "tweets_oil_gas_combined.csv")


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
# BUILD combined_tweets.csv
# ==============================

all_tweets = []

for filename in os.listdir(timelines_dir):
    if filename.endswith(".csv"):
        file_path = os.path.join(timelines_dir, filename)
        username = filename.replace(".csv", "")

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
            print(f"Skipping invalid file: {filename}")
            continue

        df = df[["created_at", "text"]].copy()
        df["publisher"] = username

        df = df.dropna(subset=["created_at", "text"])

        all_tweets.append(df)


if all_tweets:
    combined_tweets = pd.concat(all_tweets, ignore_index=True)

    combined_tweets = combined_tweets.drop_duplicates(
        subset=["created_at", "text", "publisher"]
    )

    combined_tweets.to_csv(
        combined_tweets_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("Updated combined_tweets.csv")
    print("Rows:", len(combined_tweets))

else:
    combined_tweets = pd.DataFrame(columns=["created_at", "text", "publisher"])

    combined_tweets.to_csv(
        combined_tweets_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("No tweet files found. Created empty combined_tweets.csv")


# ==============================
# LOAD TWEETS
# ==============================

tweets = pd.read_csv(combined_tweets_file, encoding="utf-8-sig")

if not tweets.empty:
    tweets = tweets[["created_at", "text", "publisher"]].copy()

    tweets["date"] = pd.to_datetime(
        tweets["created_at"],
        errors="coerce",
        utc=True
    ).dt.strftime("%Y-%m-%d")

    tweets = tweets.dropna(subset=["date"])

    tweets = tweets[["date", "text", "publisher"]]

else:
    tweets = pd.DataFrame(columns=["date", "text", "publisher"])


# ==============================
# LOAD OIL
# ==============================

oil = pd.read_csv(oil_file, encoding="utf-8-sig")

oil = oil.rename(columns={
    "תאריך": "date",
    "שער": "oil_price",
    "פתיחה": "oil_open",
    "גבוה": "oil_high",
    "נמוך": "oil_low",
    "נפח": "oil_volume",
    "שינוי %": "oil_change_percent",
    "שינוי": "oil_change_percent"
})

needed_oil_cols = [
    "date",
    "oil_price",
    "oil_open",
    "oil_high",
    "oil_low",
    "oil_volume",
    "oil_change_percent"
]

oil = oil[needed_oil_cols].copy()

oil["date"] = pd.to_datetime(
    oil["date"],
    dayfirst=True,
    errors="coerce"
).dt.strftime("%Y-%m-%d")

oil = oil.dropna(subset=["date"])

oil["oil_change_percent"] = oil["oil_change_percent"].apply(normalize_change_percent)

oil = oil.drop_duplicates(subset=["date"])
oil = oil.sort_values("date")


# ==============================
# MERGE TWEETS + OIL
# ==============================

tweet_rows = tweets.merge(oil, on="date", how="left")

dates_with_tweets = set(tweets["date"])

oil_no_tweet = oil[~oil["date"].isin(dates_with_tweets)].copy()
oil_no_tweet["text"] = "EMPTY"
oil_no_tweet["publisher"] = "EMPTY"

final_df = pd.concat([tweet_rows, oil_no_tweet], ignore_index=True)

final_df = final_df[
    [
        "date",
        "text",
        "publisher",
        "oil_price",
        "oil_open",
        "oil_high",
        "oil_low",
        "oil_volume",
        "oil_change_percent"
    ]
]

final_df = final_df.sort_values(["date", "publisher", "text"])


# ==============================
# SAVE
# ==============================

final_df.to_csv(output_file, index=False, encoding="utf-8-sig")

print("Saved combined file to:")
print(output_file)

print("\nSample:")
print(final_df.head(20))