"""Create the schema and load the manually maintained seed CSVs (dropzones, jump aircraft) into Postgres.

Safe to rerun: existing rows are updated instead of duplicated.
"""
import argparse
import os
from pathlib import Path

import pandas as pd

from sqlalchemy import URL, create_engine, text

SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def upsert(connection, table, df, key):
    """Insert rows; rows whose key already exists are updated."""
    columns = ", ".join(df.columns)
    values = ", ".join(f":{c}" for c in df.columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in df.columns if c != key)
    connection.execute(
        text(f"INSERT INTO public.{table} ({columns}) VALUES ({values}) "
             f"ON CONFLICT ({key}) DO UPDATE SET {updates}"),
        df.to_dict("records"),
    )


def load_dropzones(file_path, connection):
    """Load the Swiss dropzone CSV into swiss_dropzone."""

    dropzones = pd.read_csv(file_path).rename(columns={
        "dz_id": "dropzone_id", "name": "fullname", "lat": "latitude", "lon": "longitude",
    })
    if dropzones.empty:
        raise ValueError("The dropzone CSV is empty; existing database rows were not changed.")

    upsert(connection, "swiss_dropzone", dropzones, "dropzone_id")
    print(f"Loaded {len(dropzones):,} rows into swiss_dropzone.")


def load_jump_aircraft(file_path, connection):
    """Load the jump aircraft CSV into jump_aircraft."""

    jump_aircraft = pd.read_csv(file_path, dtype=str).rename(columns={
        "dz_id": "dropzone_id", "registration": "registration_id",
    })
    if jump_aircraft.empty:
        raise ValueError("The jump aircraft CSV is empty; existing database rows were not changed.")

    upsert(connection, "jump_aircraft", jump_aircraft, "registration_id")
    print(f"Loaded {len(jump_aircraft):,} rows into jump_aircraft.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dropzones", default="data/swiss_dropzones.csv", help="Path to the dropzone CSV")
    parser.add_argument("--jump-aircraft", default="data/jump_aircraft.csv", help="Path to the jump aircraft CSV")
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
            connection.execute(text(SCHEMA.read_text()))
            load_dropzones(args.dropzones, connection)  # first, jump_aircraft references it
            load_jump_aircraft(args.jump_aircraft, connection)
    finally:
        engine.dispose()
