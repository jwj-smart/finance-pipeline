import pandas as pd
import requests
from bs4 import BeautifulSoup
from fredapi import Fred

from config.config import FRED_API_KEY, db_engine


def get_policy_lookup():
    """Queries dim_assets to map our policy tickers to their IDs."""
    print("🔍 Fetching policy rate lookup maps from dim_assets...")
    query = "SELECT asset_id, ticker FROM dim_assets WHERE asset_class = 'Policy Rate';"
    df = pd.read_sql(query, con=db_engine)
    return dict(zip(df["ticker"], df["asset_id"]))


def scrape_and_densify_boe(asset_id):
    """Scrapes BoE rate changes, creates a daily timeline, and forward-fills values correctly."""
    print(f"🕸️ Scraping and forward-filling BoE Policy Rate (Asset ID: {asset_id})...")
    url = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    response = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    parsed_rows = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 2:
            parsed_rows.append(
                {
                    "calendar_date": pd.to_datetime(
                        cells[0].get_text(strip=True),
                        format="%d %b %y",
                        errors="coerce",
                    ),
                    "close_price": pd.to_numeric(
                        cells[1].get_text(strip=True), errors="coerce"
                    ),
                }
            )

    # 1. Force the scraped changes into an absolute chronological order (oldest first)
    df_changes = (
        pd.DataFrame(parsed_rows)
        .dropna()
        .sort_values("calendar_date", ascending=True)
        .reset_index(drop=True)
    )

    # 2. Create the daily master baseline
    full_timeline = pd.date_range(
        start="2016-01-01", end=pd.Timestamp.today(), freq="D"
    )
    df_daily = pd.DataFrame({"calendar_date": full_timeline}).sort_values(
        "calendar_date", ascending=True
    )

    # 3. Left-join changes onto the baseline
    df_merged = pd.merge(df_daily, df_changes, on="calendar_date", how="left")

    # 4. CRITICAL FIX: Sort ascending, use a singular forward fill to cascade forward in time.
    # We only use bfill() at the very end to catch the first few days of Jan 2016 before the first scraped change.
    df_merged = df_merged.sort_values("calendar_date", ascending=True)
    df_merged["close_price"] = df_merged["close_price"].ffill().bfill()

    # Final Schema Alignment
    df_merged["date_id"] = df_merged["calendar_date"].dt.strftime("%Y%m%d").astype(int)
    df_merged["asset_id"] = asset_id
    df_merged["close_price"] = df_merged["close_price"].astype(float).round(4)

    for col in ["open_price", "high_price", "low_price", "volume"]:
        df_merged[col] = None

    return df_merged[
        [
            "date_id",
            "asset_id",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]
    ]


def fetch_fred_policy(fred_client, ticker, asset_id):
    """Extracts daily central bank history directly from FRED."""
    print(f"📥 Extracting FRED policy history for: {ticker} (Asset ID: {asset_id})...")
    series_data = fred_client.get_series(ticker, observation_start="2016-01-01")

    if series_data.empty:
        return pd.DataFrame()

    df = series_data.to_frame(name="close_price").reset_index()
    df.rename(columns={"index": "calendar_date"}, inplace=True)
    df.dropna(subset=["close_price"], inplace=True)

    df["date_id"] = df["calendar_date"].dt.strftime("%Y%m%d").astype(int)
    df["asset_id"] = asset_id
    df["close_price"] = df["close_price"].astype(float).round(4)

    for col in ["open_price", "high_price", "low_price", "volume"]:
        df[col] = None

    return df[
        [
            "date_id",
            "asset_id",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]
    ]


def seed_policy_rates():
    print("🚀 Running Unified Central Bank Policy Seeding...")
    fred = Fred(api_key=FRED_API_KEY)
    policy_lookup = get_policy_lookup()

    all_chunks = []

    for ticker, asset_id in policy_lookup.items():
        try:
            if ticker == "OFFICIALBANKRATE":
                # Route the BoE ticker to our custom scraper engine
                df_transformed = scrape_and_densify_boe(asset_id)
            else:
                # Route Fed and ECB tickers to the FRED client engine
                df_transformed = fetch_fred_policy(fred, ticker, asset_id)

            if not df_transformed.empty:
                all_chunks.append(df_transformed)
        except Exception as e:
            print(f"❌ Failed processing ticker {ticker}: {str(e)}")

    if not all_chunks:
        print("❌ No data structures compiled. Aborting write.")
        return

    master_df = pd.concat(all_chunks, ignore_index=True)
    print(
        f"\n📦 Compiled master payload: {len(master_df)} total records ready for delivery."
    )

    print("📤 Bulk streaming policy rows to 'fact_market_prices'...")
    try:
        master_df.to_sql(
            name="fact_market_prices",
            con=db_engine,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
        print("🎉 Policy rates successfully integrated into fact table!")
    except Exception as e:
        print(f"❌ Database write failure: {str(e)}")


if __name__ == "__main__":
    seed_policy_rates()
