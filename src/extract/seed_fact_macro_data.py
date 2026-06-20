import pandas as pd
from fredapi import Fred

from config.config import FRED_API_KEY, db_engine


def get_macro_lookup():
    """Queries dim_macro_indicators to create an indicator_code-to-id mapping dictionary."""
    print("🔍 Fetching macro indicators lookup map from warehouse...")
    query = "SELECT indicator_id, indicator_code FROM dim_macro_indicators;"
    df = pd.read_sql(query, con=db_engine)
    return dict(zip(df["indicator_code"], df["indicator_id"]))


def fetch_and_transform_macro_history(fred_client, code, indicator_id):
    """Extracts monthly historical series from FRED and transforms it to the macro fact grain."""
    print(f"📥 Extracting history for macro code: {code} (Macro ID: {indicator_id})...")

    # 1. Fetch raw time-series macro data from FRED (Back to 2016)
    series_data = fred_client.get_series(code, observation_start="2016-01-01")

    if series_data.empty:
        print(f"⚠️ Warning: No data returned for {code}")
        return pd.DataFrame()

    # 2. Convert Series to DataFrame
    df = series_data.to_frame(name="value").reset_index()
    df.rename(columns={"index": "calendar_date"}, inplace=True)

    # 3. Clean and filter values
    df.dropna(subset=["value"], inplace=True)

    # 4. Transform attributes to align with star schema constraints
    df["date_id"] = df["calendar_date"].dt.strftime("%Y%m%d").astype(int)
    df["indicator_id"] = indicator_id
    df["value"] = df["value"].astype(float).round(4)

    # Isolate exact columns matching your fact table schema layout
    fact_columns = ["date_id", "indicator_id", "value"]
    return df[fact_columns]


def seed_macro_fact_table():
    print("🚀 Initiating Historical Macro Data Fact Seeding...")

    # Initialize infrastructure elements
    fred = Fred(api_key=FRED_API_KEY)
    macro_lookup = get_macro_lookup()

    all_chunks = []

    # Ingest data code by code
    for code, indicator_id in macro_lookup.items():
        try:
            df_transformed = fetch_and_transform_macro_history(fred, code, indicator_id)
            if not df_transformed.empty:
                all_chunks.append(df_transformed)
        except Exception as e:
            print(f"❌ Failed processing macro indicator {code}: {str(e)}")

    if not all_chunks:
        print("❌ No historical macro data was pulled successfully. Aborting write.")
        return

    # Combine individual dataframes into one master payload
    master_macro_df = pd.concat(all_chunks, ignore_index=True)
    print(
        f"\n📦 Master payload compiled: {len(master_macro_df)} total rows ready for delivery."
    )

    # 5. Push data down the pipeline via WAN chunking
    print("📤 Commencing bulk stream to Supabase...")
    try:
        master_macro_df.to_sql(
            name="fact_macro_data",
            con=db_engine,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
        print(
            "🎉 Successfully seeded fact_macro_data! Historical economic indexes are live."
        )
    except Exception as e:
        print(f"❌ Database load failure: {str(e)}")


if __name__ == "__main__":
    seed_macro_fact_table()
