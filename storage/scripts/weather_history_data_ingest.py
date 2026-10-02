"""Create the schema and load the manually maintained seed CSVs (dropzones, jump aircraft) into Postgres.

Safe to rerun: existing rows are updated instead of duplicated.
"""
import argparse
import os
from pathlib import Path

import pandas as pd

from sqlalchemy import URL, create_engine, text

def upsert(connection, table, df, keys):
    """Insert rows; rows whose keys already exist are updated."""
    columns = ", ".join(df.columns)
    values = ", ".join(f":{c}" for c in df.columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in df.columns if c not in keys)
    connection.execute(
        text(f"INSERT INTO public.{table} ({columns}) VALUES ({values}) "
             f"ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {updates}"),
        df.to_dict("records"),
    )


def load_weather_history(file_path, connection):
    """Load the weather history CSV into weather_history."""

    dz_id = file_path.stem.split("_")[1]

    # cspell:ignore weathercode
    weather_history = pd.read_csv(file_path, dtype=str)
    if "dropzone_id" not in weather_history.columns:
        weather_history["dropzone_id"] = dz_id
    else:
        weather_history["dropzone_id"] = weather_history["dropzone_id"].fillna(dz_id)

    weather_history = weather_history.rename(columns={
        "date": "timestamp",
        "temperature_2m": "temperature_2m_c",
        "wind_speed_10m": "wind_speed_10m_mps",
        "wind_gusts_10m": "wind_gusts_10m_mps",
        "cloud_cover_low": "cloud_cover_low_percent",
        "precipitation": "precipitation_mm",
        "visibility": "visibility_m",
        "wind_speed_850hPa": "wind_speed_850hpa_mps",
        "wind_speed_700hPa": "wind_speed_700hpa_mps",
    })
    if weather_history.empty:
        raise ValueError("The weather history CSV is empty; existing database rows were not changed.")

    upsert(connection, "weather_history", weather_history, ("dropzone_id", "timestamp"))
    print(f"Loaded {len(weather_history):,} rows into weather_history.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path("data/past"), help="Folder with the weather history CSVs")
    args = parser.parse_args()
    url = URL.create(
        "postgresql+psycopg", host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)), database=os.environ["POSTGRES_DB"],
        username=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    engine = create_engine(url, connect_args={"connect_timeout": 10}, hide_parameters=True)
    try:
        # One transaction: either both tables are loaded or nothing changes
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            for file_path in sorted(args.dir.glob("*.csv")):
                load_weather_history(file_path, connection)
    finally:
        engine.dispose()
