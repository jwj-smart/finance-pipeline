import holidays
import pandas as pd

from config.config import db_engine


def generate_market_calendar(start_year: int = 2016, end_year: int = 2035):
    print(f"Generate financial calendar dimension from {start_year} to {end_year}...")

    # Create continuous frequency array of daily timestamps
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # Initialise the UK holiday engine (Specifically England/Wales bank holidays)
    uk_holidays = holidays.UK(subdiv="England")

    # Construct the dataframe row-by-row via vectorised Pandas attributes
    df = pd.DataFrame({"calendar_date": date_range})

    # Derive Kimball surrogate key (YYYYMMDD integer)
    df["date_id"] = df["calendar_date"].dt.strftime("%Y%m%d").astype(int)

    # Base attributes
    df["year"] = df["calendar_date"].dt.year
    df["quarter"] = df["calendar_date"].dt.quarter
    df["month_number"] = df["calendar_date"].dt.month
    df["month_name"] = df["calendar_date"].dt.strftime("%B")
    df["day_name"] = df["calendar_date"].dt.strftime("%A")

    # Apply financial logical flags
    df["is_weekend"] = df["calendar_date"].dt.dayofweek.isin(
        [5, 6]
    )  # Saturday=5, Sunday=6

    # Vectorised evaluation: checking if date is in the UK holiday catalogue
    is_holiday = df["calendar_date"].apply(lambda x: x in uk_holidays)

    # Market budiness Day logic: NOT a weekend and NOT an official Bank holiday
    df["is_uk_business_day"] = ~(df["is_weekend"] | is_holiday)

    # Reorder columns to align exactly with Supabase DDL schema layout
    column_order = [
        "date_id",
        "calendar_date",
        "year",
        "quarter",
        "month_number",
        "month_name",
        "day_name",
        "is_weekend",
        "is_uk_business_day",
    ]

    return df[column_order]


def load_calendar_to_warehouse():
    calendar_df = generate_market_calendar()

    print("Pushing calendar to Supabase...")
    try:
        # chunksize split force optimal transmission batch size over WAN
        calendar_df.to_sql(
            name="dim_date",
            con=db_engine,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
        print("Successfully seeded dim_date! Warehouse time anchor is locked down.")
    except Exception as e:
        print(f"Database load failure: {str(e)}")


if __name__ == "__main__":
    load_calendar_to_warehouse()
