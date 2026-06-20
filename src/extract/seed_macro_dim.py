import pandas as pd

from config.config import db_engine


def seed_macro_dimension():
    print("📈 Initializing macroeconomic indicators dimension...")

    # Mapping exact FRED Series IDs for your structural economic indicators
    macro_data = [
        {
            "indicator_code": "GBRCPIALLMINMEI",
            "indicator_name": "UK Consumer Price Index (CPI) YoY Inflation",
            "frequency": "Monthly",
        },
        {
            "indicator_code": "ILMTOPSUKM",
            "indicator_name": "UK Unemployment Rate",
            "frequency": "Monthly",
        },
        {
            "indicator_code": "AUKPPI01GBM661N",
            "indicator_name": "UK Producer Price Index (PPI)",
            "frequency": "Monthly",
        },
    ]

    df_macro = pd.DataFrame(macro_data)

    print(f"🚀 Pushing {len(df_macro)} items to 'dim_macro_indicators' table...")
    try:
        df_macro.to_sql(
            name="dim_macro_indicators", con=db_engine, if_exists="append", index=False
        )
        print("🎉 Macroeconomic indicators dimension successfully seeded!")

    except Exception as e:
        print(f"❌ Failed to seed macro indicators: {str(e)}")


if __name__ == "__main__":
    seed_macro_dimension()
