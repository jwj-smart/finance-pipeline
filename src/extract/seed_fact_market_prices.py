import pandas as pd
from fredapi import Fred

from config.config import FRED_API_KEY, db_engine


def get_asset_lookup():
    """Queries dim_assets from Supabase to create a local ticker-to-id mapping dictionary."""
    print("🔍 Fetching asset lookup map from data warehouse...")
    query = "SELECT asset_id, ticker FROM dim_assets WHERE is_benchmark = TRUE;"
    df = pd.read_sql(query, con=db_engine)

    # Creates a handy dictionary: {'IURSONIA': 1, 'SOFR': 2, ...}
    return dict(zip(df["ticker"], df["asset_id"]))


def fetch_and_transform_fred_history(fred_client, ticker, asset_id):
    """Extracts 10-year historical series from FRED and transforms it to the fact table grain."""
    print(f"📥 Extracting history for ticker: {ticker} (Asset ID: {asset_id})...")

    # 1. Fetch raw time-series data from FRED (Back to 2016)
    series_data = fred_client.get_series(ticker, observation_start="2016-01-01")

    if series_data.empty:
        print(f"⚠️ Warning: No data returned for {ticker}")
        return pd.DataFrame()

    # 2. Convert Series to DataFrame
    df = series_data.to_frame(name="close_price").reset_index()
    df.rename(columns={"index": "calendar_date"}, inplace=True)

    # 3. Drop rows with null values (FRED represents weekend/holiday closures as NaN)
    df.dropna(subset=["close_price"], inplace=True)

    # 4. Transform attributes to align with star schema constraints
    df["date_id"] = df["calendar_date"].dt.strftime("%Y%m%d").astype(int)
    df["asset_id"] = asset_id

    # High-precision numeric rounding matching our NUMERIC(12, 4) database type
    df["close_price"] = df["close_price"].astype(float).round(4)

    # FRED interest rates are single values, so open/high/low/volume are null for these benchmarks
    df["open_price"] = None
    df["high_price"] = None
    df["low_price"] = None
    df["volume"] = None

    # Filter the exact columns matching your fact table layout
    fact_columns = [
        "date_id",
        "asset_id",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    ]
    return df[fact_columns]


def seed_market_prices_fact():
    print("🚀 Initiating Historical Market Prices Fact Seeding...")

    # Initialize FRED client and asset registry
    fred = Fred(api_key=FRED_API_KEY)
    asset_lookup = get_asset_lookup()

    all_chunks = []

    # Ingest data ticker by ticker
    for ticker, asset_id in asset_lookup.items():
        try:
            df_transformed = fetch_and_transform_fred_history(fred, ticker, asset_id)
            if not df_transformed.empty:
                all_chunks.append(df_transformed)
        except Exception as e:
            print(f"❌ Failed processing ticker {ticker}: {str(e)}")

    if not all_chunks:
        print("❌ No historical data was pulled successfully. Aborting database write.")
        return

    # Combine individual dataframes into one master payload
    master_fact_df = pd.concat(all_chunks, ignore_index=True)
    print(
        f"\n📦 Master payload compiled: {len(master_fact_df)} total rows ready for delivery."
    )

    # 5. Pushing data down the pipeline using our optimized WAN chunking strategy
    print("📤 Commencing bulk stream to Supabase...")
    try:
        master_fact_df.to_sql(
            name="fact_market_prices",
            con=db_engine,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
        print(
            "🎉 Successfully seeded fact_market_prices! Historical benchmark data is live."
        )
    except Exception as e:
        print(f"❌ Database load failure: {str(e)}")


if __name__ == "__main__":
    seed_market_prices_fact()
