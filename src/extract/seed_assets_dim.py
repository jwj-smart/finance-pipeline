import pandas as pd

from config.config import db_engine


def seed_assets_dimension():
    print("📦 Initializing asset dimension catalog...")

    # Unified reference frame mapping exact FRED tickers for direct API passing later
    assets_data = [
        {
            "ticker": "IURSONIA",
            "asset_name": "Sterling Overnight Index Average (SONIA)",
            "asset_class": "Benchmark",
            "currency": "GBP",
            "is_benchmark": True,
        },
        {
            "ticker": "SOFR",
            "asset_name": "Secured Overnight Financing Rate (SOFR)",
            "asset_class": "Benchmark",
            "currency": "USD",
            "is_benchmark": True,
        },
        {
            "ticker": "ECBESTRVOLWGTTRMDMNRT",
            "asset_name": "Euro Short-Term Rate (€STR)",
            "asset_class": "Benchmark",
            "currency": "EUR",
            "is_benchmark": True,
        },
        {
            "ticker": "GB10Y=F",
            "asset_name": "UK 10-Year Gilt Futures",
            "asset_class": "Fixed Income",
            "currency": "GBP",
            "is_benchmark": False,
        },
        {
            "ticker": "^FTSE",
            "asset_name": "FTSE 100 Index",
            "asset_class": "Equity",
            "currency": "GBP",
            "is_benchmark": False,
        },
    ]

    df_assets = pd.DataFrame(assets_data)

    print(f"🚀 Pushing {len(df_assets)} items to 'dim_assets' table...")
    try:
        # Append directly. PK constraints protect integrity if re-run
        df_assets.to_sql(
            name="dim_assets", con=db_engine, if_exists="append", index=False
        )
        print("🎉 Asset catalog dimension successfully seeded!")

    except Exception as e:
        print(f"❌ Failed to seed asset catalog: {str(e)}")


if __name__ == "__main__":
    seed_assets_dimension()
