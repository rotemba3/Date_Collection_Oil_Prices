import os
import time
import pandas as pd
from datetime import datetime, timedelta

from twikit import Client
from SearchScrapper import SearchScrapper

# CHANGED: BASE_DIR is now relative to this file's location in the repo,
# instead of a hardcoded Windows path. Everything under it (Scraper/, Data/,
# combined_tweets.csv, the oil CSV) keeps the same subfolder layout you
# already had — only the root moved from C:\Users\... to "wherever this
# repo is checked out."
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE  = os.path.join(BASE_DIR, "Scraper", "twitter_usernames_for_scraper.xlsx")
OUT_DIR     = os.path.join(BASE_DIR, "Data", "Users_Timelines")

# Combined tweets file — used to find last scraped date
COMBINED_TWEETS_FILE = os.path.join(BASE_DIR, "combined_tweets.csv")

# CHANGED: the oil price CSV used to be downloaded by clicking a button on
# investing.com with Selenium. GitHub Actions has no browser/Downloads
# folder to do that with, so it's now fetched directly via yfinance (see
# fetch_oil_csv() below). The output file keeps the exact same name/path
# and the exact same Hebrew column format investing.com used to produce,
# so combine_data.py needs ZERO changes.
OIL_TARGET_PATH = os.path.join(
    BASE_DIR,
    "_WTI - חוזים עתידיים על נפט גולמי - נתונים היסטוריים.csv"
)
OIL_TICKER = "CL=F"  # WTI Crude Oil futures on Yahoo Finance

# Absolute earliest date to ever scrape from (historical backfill start)
SCRAPE_HISTORY_START = "2026-6-01"

# Set to True to ignore existing data and re-scrape everything from SCRAPE_HISTORY_START.
# Set back to False after the full rescrape is done so daily runs only fetch new tweets.
FORCE_FULL_RESCRAPE = True


# ==============================
# DETERMINE SCRAPE START DATE
# ==============================

def get_scrape_start_date():
    """
    Returns the date to scrape FROM.
    - If FORCE_FULL_RESCRAPE is True, always start from SCRAPE_HISTORY_START.
    - Otherwise use (last scraped date - 2 days) for incremental daily updates.
    """
    if FORCE_FULL_RESCRAPE:
        print(f"FORCE_FULL_RESCRAPE=True → scraping from: {SCRAPE_HISTORY_START}")
        return SCRAPE_HISTORY_START

    if os.path.exists(COMBINED_TWEETS_FILE):
        try:
            existing = pd.read_csv(COMBINED_TWEETS_FILE, encoding="utf-8-sig")

            if not existing.empty and "created_at" in existing.columns:
                existing["_date"] = pd.to_datetime(
                    existing["created_at"], errors="coerce", utc=True
                )
                last_date = existing["_date"].dropna().max()

                if pd.notna(last_date):
                    # Go back 2 days for overlap safety
                    start = (last_date - timedelta(days=2)).strftime("%Y-%m-%d")
                    print(f"Last scraped date: {last_date.date()}")
                    print(f"Scraping from:     {start}  (2-day overlap)")
                    return start

        except Exception as e:
            print(f"Could not read combined_tweets.csv: {e}")

    print(f"No existing data found. Scraping from history start: {SCRAPE_HISTORY_START}")
    return SCRAPE_HISTORY_START


# ==============================
# TWITTER FUNCTIONS
# ==============================

def load_usernames(input_path=INPUT_FILE, column="Twitter_username", limit=None):
    df = pd.read_excel(input_path)

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found. Available: {list(df.columns)}")

    users = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .str.replace("@", "", regex=False)
    )

    users = users[users != ""].unique().tolist()

    if limit is not None:
        users = users[:limit]

    print(f"Loaded {len(users)} usernames.")
    return users


def scrape_user(client, username, start_date, end_date, max_tweets=5000):
    # CHANGED: twikit takes a plain query string, not a x.com search URL.
    search_query = f"(from:{username}) since:{start_date} until:{end_date}"

    scraped = SearchScrapper(client).scrape_twitter_query(
        search_query,
        username,
        max_tweets=max_tweets
    )

    rows = []
    for t in scraped:
        rows.append({
            "tweet_id":   getattr(t, "ID", None),
            "created_at": getattr(t, "timestamp", None),
            "text":       getattr(t, "content", None),
            "replies":    getattr(t, "comments", None),
            "retweets":   getattr(t, "retweets", None),
            "likes":      getattr(t, "likes", None),
        })

    return rows


def save_user_timeline(out_dir, username, rows):
    """
    APPEND new tweets to existing user file instead of overwriting.
    Deduplicates by (created_at, text).
    """
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{username}.csv")

    new_df = pd.DataFrame(
        rows,
        columns=["tweet_id", "created_at", "text", "replies", "retweets", "likes"]
    )

    if os.path.exists(out_path):
        try:
            existing_df = pd.read_csv(out_path, encoding="utf-8-sig")
            combined    = pd.concat([existing_df, new_df], ignore_index=True)
            combined    = combined.drop_duplicates(subset=["created_at", "text"])
        except Exception:
            combined = new_df
    else:
        combined = new_df

    combined.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def scrape_twitter_users(client):
    print("\n==============================")
    print("Scraping Twitter/X users")
    print("==============================")

    start_date = get_scrape_start_date()
    end_date   = datetime.today().strftime("%Y-%m-%d")

    print(f"Date window: {start_date} → {end_date}")

    users = load_usernames()

    for i, user in enumerate(users, 1):
        try:
            print(f"\n[{i}/{len(users)}] Scraping @{user} ...")

            rows = scrape_user(
                client,
                user,
                start_date,
                end_date,
                max_tweets=5000
            )

            out_path = save_user_timeline(OUT_DIR, user, rows)

            print(f"Saved {len(rows)} tweets → {out_path}")

            time.sleep(2)

        except Exception as e:
            print(f"Failed @{user}: {e}")


# ==============================
# OIL DOWNLOAD FUNCTIONS
# ==============================
# CHANGED: replaces the Selenium click-through-investing.com flow. Pulls
# the same WTI crude data via yfinance and writes it in the identical
# Hebrew-header, dd/mm/yyyy CSV format investing.com used to produce, so
# combine_data.py (which parses that exact format) doesn't need to change.

def fetch_oil_csv():
    import yfinance as yf

    print("\n==============================")
    print("Downloading latest oil CSV (yfinance)")
    print("==============================")

    data = yf.download(OIL_TICKER, period="180d", interval="1d", progress=False)
    if data.empty:
        print("yfinance returned no data.")
        return False

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.sort_index()
    change_pct = data["Close"].pct_change() * 100

    out = pd.DataFrame({
        "תאריך":   data.index.strftime("%d/%m/%Y"),
        "שער":     data["Close"].round(2),
        "פתיחה":   data["Open"].round(2),
        "גבוה":    data["High"].round(2),
        "נמוך":    data["Low"].round(2),
        "נפח":     data["Volume"].fillna(0).astype(int),
        "שינוי %": change_pct.round(2).astype(str) + "%",
    })

    # investing.com's export is newest-first — match that ordering.
    out = out.iloc[::-1]

    out.to_csv(OIL_TARGET_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved oil CSV: {OIL_TARGET_PATH} ({len(out)} rows)")
    return True


# ==============================
# MAIN
# ==============================
# CHANGED: no more Selenium driver setup. twikit authenticates with saved
# login cookies (see GUIDE.md for how to generate these once, locally) —
# read from the TWITTER_COOKIES environment variable / GitHub secret so
# nothing is hardcoded in this file.

def setup_twikit_client():
    cookies_json = os.environ.get("TWITTER_COOKIES")
    if not cookies_json:
        raise RuntimeError(
            "TWITTER_COOKIES environment variable is not set. "
            "See GUIDE.md for how to generate and store it."
        )

    cookies_path = os.path.join(BASE_DIR, "cookies.json")
    with open(cookies_path, "w", encoding="utf-8") as f:
        f.write(cookies_json)

    client = Client("en-US")
    client.load_cookies(cookies_path)
    return client, cookies_path


def main():
    client, cookies_path = setup_twikit_client()

    try:
        fetch_oil_csv()
        scrape_twitter_users(client)

    finally:
        if os.path.exists(cookies_path):
            os.remove(cookies_path)  # don't leave credentials on disk


if __name__ == "__main__":
    main()