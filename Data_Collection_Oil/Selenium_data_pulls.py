import os
import time
import pandas as pd
from WebDriverSetup import setup_web_driver
from SearchScrapper import SearchScrapper


def load_usernames(input_path="twitter_usernames_for_scraper.xlsx", column="user_name", limit=None):
    df = pd.read_excel(input_path)

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found. Available columns: {list(df.columns)}")

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

    print(f"Loaded {len(users)} usernames from '{input_path}' column '{column}'.")
    return users


def save_user_timeline(out_dir, username, rows):
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{username}.csv")
    df = pd.DataFrame(rows, columns=["tweet_id", "created_at", "text", "replies", "retweets", "likes"])
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def scrape_user(driver, username, start_date, end_date, max_tweets=5000):
    search_query = (
        f"https://x.com/search?q=%28from%3A{username}%29+until%3A{end_date}+since%3A{start_date}"
        f"&src=typed_query&f=live"
    )

    scraped = SearchScrapper(driver).scrape_twitter_query(
        search_query, username, max_tweets=max_tweets
    )

    rows = []
    for t in scraped:
        rows.append({
            "tweet_id": getattr(t, "ID", None),
            "created_at": getattr(t, "timestamp", None),
            "text": getattr(t, "content", None),
            "replies": getattr(t, "comments", None),
            "retweets": getattr(t, "retweets", None),
            "likes": getattr(t, "likes", None),
        })
    return rows


def main():
    driver = setup_web_driver()

    try:
        input_file = "twitter_usernames_for_scraper.xlsx"
        out_dir = os.path.join("Data", "Users_Timelines")

        start_date = "2025-12-01"
        end_date = "2026-03-26"

        users = load_usernames(input_file, column="Twitter_username")

        for i, user in enumerate(users, 1):
            try:
                print(f"\n[{i}/{len(users)}] Scraping @{user} ...")
                rows = scrape_user(driver, user, start_date, end_date, max_tweets=5000)

                out_path = save_user_timeline(out_dir, user, rows)
                print(f"✔ Saved {len(rows)} tweets -> {out_path}")

                time.sleep(2)
            except Exception as e:
                print(f"✖ Failed @{user}: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()