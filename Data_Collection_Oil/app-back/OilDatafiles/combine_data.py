import pandas as pd
import os

# ==============================
# FILE PATHS
# ==============================

base_dir = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

tweets_file = os.path.join(base_dir, "combined_tweets.csv")
oil_file = os.path.join(base_dir, "_WTI - חוזים עתידיים על נפט גולמי - נתונים היסטוריים.csv")
gas_file = os.path.join(base_dir, "stationprice2025.xlsx")   # add 2026 later if needed
output_file = os.path.join(base_dir, "tweets_oil_gas_combined.csv")

# ==============================
# HELPER
# ==============================

def clean_numeric(val):
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).replace(",", "").replace("%", "").strip()

    multiplier = 1
    if s.endswith("K"):
        multiplier = 1_000
        s = s[:-1]
    elif s.endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]

    try:
        return float(s) * multiplier
    except:
        return None

# ==============================
# LOAD TWEETS
# ==============================

tweets = pd.read_csv(tweets_file, encoding="utf-8-sig")
tweets = tweets[["created_at", "text", "publisher"]].copy()

tweets = tweets.rename(columns={"created_at": "date"})
tweets["date"] = pd.to_datetime(tweets["date"], errors="coerce")
tweets = tweets.dropna(subset=["date"])
tweets["date"] = tweets["date"].dt.strftime("%Y-%m-%d")

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
    "שינוי %": "oil_change_percent"
})

oil["date"] = pd.to_datetime(oil["date"], dayfirst=True, errors="coerce")
oil = oil.dropna(subset=["date"])
oil = oil.sort_values("date")

for col in ["oil_price", "oil_open", "oil_high", "oil_low", "oil_volume", "oil_change_percent"]:
    if col in oil.columns:
        oil[col] = oil[col].apply(clean_numeric)

# add yesterday oil price
oil["oil_price_yesterday"] = oil["oil_price"].shift(1)

# date back to string for clean merge
oil["date"] = oil["date"].dt.strftime("%Y-%m-%d")

# ==============================
# LOAD GAS (HEADERS AT LINE 6)
# ==============================

gas = pd.read_excel(gas_file, skiprows=5)

print("Gas columns:", gas.columns.tolist())
print(gas.head())

gas = gas.rename(columns={
    "תאריך": "date",
    "בנזין 95 אוקטן נטול עופרת": "gas_price",
    "תוספת בעד שירות מלא": "full_service_extra",
    "תוספת שירות מלא": "full_service_extra"
})

if "date" not in gas.columns:
    raise ValueError(f"Gas date column not found. Columns: {gas.columns.tolist()}")

if "gas_price" not in gas.columns:
    raise ValueError(f"Gas price column not found. Columns: {gas.columns.tolist()}")

gas["date"] = pd.to_datetime(gas["date"], dayfirst=True, errors="coerce")
gas = gas.dropna(subset=["date"])

gas["gas_price"] = gas["gas_price"].apply(clean_numeric)

# keep only one row per month
gas["month_key"] = gas["date"].dt.to_period("M")
gas = gas.sort_values("date").drop_duplicates(subset=["month_key"])

# ==============================
# MERGE TWEETS + OIL
# ==============================

tweet_rows = tweets.merge(oil, on="date", how="left")

# create EMPTY rows for oil dates that have no tweet
dates_with_tweets = set(tweets["date"])
oil_no_tweet = oil[~oil["date"].isin(dates_with_tweets)].copy()
oil_no_tweet["text"] = "EMPTY"
oil_no_tweet["publisher"] = "EMPTY"

# align columns
tweet_rows["date"] = pd.to_datetime(tweet_rows["date"], errors="coerce")
oil_no_tweet["date"] = pd.to_datetime(oil_no_tweet["date"], errors="coerce")

# ==============================
# ADD GAS PRICE BY MONTH
# ==============================

tweet_rows["month_key"] = tweet_rows["date"].dt.to_period("M")
oil_no_tweet["month_key"] = oil_no_tweet["date"].dt.to_period("M")

tweet_rows = tweet_rows.merge(
    gas[["month_key", "gas_price"]],
    on="month_key",
    how="left"
)

oil_no_tweet = oil_no_tweet.merge(
    gas[["month_key", "gas_price"]],
    on="month_key",
    how="left"
)

# ==============================
# COMBINE FINAL
# ==============================

final_df = pd.concat([tweet_rows, oil_no_tweet], ignore_index=True)

final_df["date"] = final_df["date"].dt.strftime("%Y-%m-%d")

# reorder nicely
wanted_cols = [
    "date",
    "text",
    "publisher",
    "oil_price",
    "oil_price_yesterday",
    "oil_open",
    "oil_high",
    "oil_low",
    "oil_volume",
    "oil_change_percent",
    "gas_price"
]

final_df = final_df[wanted_cols]
final_df = final_df.sort_values(["date", "publisher", "text"])

# ==============================
# SAVE
# ==============================

final_df.to_csv(output_file, index=False, encoding="utf-8-sig")

print("Saved combined file to:")
print(output_file)
print("\nSample:")
print(final_df.head(20))