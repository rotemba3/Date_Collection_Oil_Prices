import os
import time
import shutil
import pandas as pd
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from WebDriverSetup import setup_web_driver
from SearchScrapper import SearchScrapper


BASE_DIR = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

INPUT_FILE = os.path.join(BASE_DIR, "Scraper", "twitter_usernames_for_scraper.xlsx")
OUT_DIR = os.path.join(BASE_DIR, "Data", "Users_Timelines")

OIL_URL = "https://il.investing.com/commodities/crude-oil-historical-data"

DOWNLOADS_FOLDER = r"C:\Users\97254\Downloads"

OIL_TARGET_PATH = os.path.join(
    BASE_DIR,
    "_WTI - חוזים עתידיים על נפט גולמי - נתונים היסטוריים.csv"
)


# ==============================
# TWITTER FUNCTIONS
# ==============================

def load_usernames(input_path=INPUT_FILE, column="Twitter_username", limit=None):
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

    print(f"Loaded {len(users)} usernames.")
    return users


def scrape_user(driver, username, start_date, end_date, max_tweets=5000):
    search_query = (
        f"https://x.com/search?q=%28from%3A{username}%29"
        f"+since%3A{start_date}+until%3A{end_date}"
        f"&src=typed_query&f=live"
    )

    scraped = SearchScrapper(driver).scrape_twitter_query(
        search_query,
        username,
        max_tweets=max_tweets
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


def save_user_timeline(out_dir, username, rows):
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"{username}.csv")

    df = pd.DataFrame(
        rows,
        columns=["tweet_id", "created_at", "text", "replies", "retweets", "likes"]
    )

    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def scrape_twitter_users(driver):
    print("\n==============================")
    print("Scraping Twitter/X users")
    print("==============================")

    start_date = "2025-12-01"
    end_date = datetime.today().strftime("%Y-%m-%d")

    users = load_usernames()

    for i, user in enumerate(users, 1):
        try:
            print(f"\n[{i}/{len(users)}] Scraping @{user} ...")

            rows = scrape_user(
                driver,
                user,
                start_date,
                end_date,
                max_tweets=5000
            )

            out_path = save_user_timeline(OUT_DIR, user, rows)

            print(f"Saved {len(rows)} tweets -> {out_path}")

            time.sleep(2)

        except Exception as e:
            print(f"Failed @{user}: {e}")


# ==============================
# OIL DOWNLOAD FUNCTIONS
# ==============================

def close_popups(driver):
    time.sleep(2)

    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")

        for btn in buttons:
            text = btn.text.strip()

            if text in ["Accept", "Agree", "I Agree", "קבל", "קבל הכל", "מסכים", "אישור"]:
                driver.execute_script("arguments[0].click();", btn)
                print("Clicked cookie button")
                time.sleep(2)
                break

    except Exception as e:
        print("Cookie close failed:", e)

    try:
        close_buttons = driver.find_elements(By.XPATH, "//*[@data-test='close-button']")

        for btn in close_buttons:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print("Closed signup/login popup")
                time.sleep(2)
                break

    except Exception as e:
        print("Popup close failed:", e)


def click_oil_download(driver):
    wait = WebDriverWait(driver, 30)

    print("\n==============================")
    print("Downloading latest oil CSV")
    print("==============================")

    driver.get(OIL_URL)
    time.sleep(7)

    close_popups(driver)

    print("Trying to click download button...")

    try:
        download_button = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(text(), 'הורדה')]/parent::div")
            )
        )

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", download_button)

        print("Clicked הורדה")
        return True

    except Exception as e:
        print("Could not click הורדה:")
        print(e)
        return False


def wait_for_download_and_copy(timeout=120):
    print("\nWaiting for CSV download to finish...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        files = os.listdir(DOWNLOADS_FOLDER)

        still_downloading = any(
            f.endswith(".crdownload") or f.endswith(".tmp")
            for f in files
        )

        if still_downloading:
            time.sleep(1)
            continue

        csv_files = [
            os.path.join(DOWNLOADS_FOLDER, f)
            for f in files
            if f.lower().endswith(".csv")
        ]

        if csv_files:
            latest_file = max(csv_files, key=os.path.getctime)

            print("Latest CSV found:")
            print(latest_file)

            if os.path.exists(OIL_TARGET_PATH):
                os.remove(OIL_TARGET_PATH)
                print("Removed old oil CSV from project.")

            shutil.copy(latest_file, OIL_TARGET_PATH)

            print("Copied oil CSV to project:")
            print(OIL_TARGET_PATH)

            return True

        time.sleep(1)

    print("No CSV download found in time.")
    return False


def download_oil_csv(driver):
    ok = click_oil_download(driver)

    if not ok:
        print("Oil download click failed.")
        return False

    copied = wait_for_download_and_copy(timeout=120)

    if not copied:
        print("Oil CSV copy failed.")
        return False

    return True


# ==============================
# MAIN
# ==============================

def main():
    driver = setup_web_driver()

    try:
        # 1. Download oil CSV from Investing and copy from Downloads to project
        download_oil_csv(driver)

        # 2. Scrape Twitter/X users
        scrape_twitter_users(driver)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()