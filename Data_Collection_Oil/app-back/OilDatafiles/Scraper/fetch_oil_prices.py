"""
Fetches daily WTI crude oil price data and writes it in the exact CSV
format/filename your old Selenium download used to produce, so
combine_data.py needs zero changes.

This has NO dependency on Selenium or twikit — it's pure yfinance, so it
keeps running automatically in GitHub Actions even while Twitter scraping
is temporarily local-only (see main.py / SearchScrapper.py / WebDriverSetup.py,
restored to their original Selenium versions — run those by hand and
git push the resulting CSVs when you want fresh tweet data included).
"""

import os
import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OIL_TARGET_PATH = os.path.join(
    BASE_DIR,
    "_WTI - חוזים עתידיים על נפט גולמי - נתונים היסטוריים.csv"
)
OIL_TICKER = "CL=F"  # WTI Crude Oil futures on Yahoo Finance


def main():
    print("\n==============================")
    print("Downloading latest oil CSV (yfinance)")
    print("==============================")

    data = yf.download(OIL_TICKER, period="180d", interval="1d", progress=False)
    if data.empty:
        raise RuntimeError("yfinance returned no oil price data.")

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

    # investing.com's export (what this replaces) was newest-first.
    out = out.iloc[::-1]

    out.to_csv(OIL_TARGET_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved oil CSV: {OIL_TARGET_PATH} ({len(out)} rows)")


if __name__ == "__main__":
    main()
