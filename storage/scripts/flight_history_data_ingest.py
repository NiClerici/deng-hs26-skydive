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


def load_flight_history(file_path, connection):
    """Load the flight history CSV into flight_history."""

    dz_id = file_path.stem.split("_")[1]

    flight_history = pd.read_csv(file_path, dtype=str)
    if "dropzone_id" not in flight_history.columns:
        flight_history["dropzone_id"] = dz_id
    else:
        flight_history["dropzone_id"] = flight_history["dropzone_id"].fillna(dz_id)

    flight_history = flight_history.rename(columns={
        "date": "timestamp",
        "icao24": "icao24",
        "callsign": "callsign",
        "DepartureAirport": "departure_airport",
        "ArrivalAirport": "arrival_airport",
        "Duration": "duration",
    })
    if flight_history.empty:
        raise ValueError("The flight history CSV is empty; existing database rows were not changed.")

    upsert(connection, "flight_history", flight_history, ("dropzone_id", "timestamp", "icao24"))
    print(f"Loaded {len(flight_history):,} rows into flight_history.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path("data/flights"), help="Folder with the flight history CSVs")
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
                load_flight_history(file_path, connection)
    finally:
        engine.dispose()
