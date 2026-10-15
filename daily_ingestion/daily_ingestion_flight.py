import os
import pandas as pd
import datetime

from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from opensky_api import OpenSkyApi
from sqlalchemy import URL, create_engine, text


TZ = ZoneInfo("Europe/Zurich")
DROPZONES_CSV = Path(__file__).resolve().parent.parent / "data" / "swiss_dropzones.csv"

load_dotenv()
api = OpenSkyApi(client_id=os.getenv("CLIENT_ID"),client_secret=os.getenv("CLIENT_SECRET"))


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


def load_flight_data():
    dropzones_df = pd.read_csv(DROPZONES_CSV, usecols=["dz_id","name"],index_col=False)
    yesterday = datetime.datetime.now(TZ).date() - datetime.timedelta(days=1)

    yesterday_03 = datetime.datetime.combine(yesterday, datetime.time(3, 0, 0), tzinfo=TZ)
    yesterday_23 = datetime.datetime.combine(yesterday, datetime.time(23, 0, 0), tzinfo=TZ)

    flight_history = {
        "date": [],"dropzone_id":[],"icao24": [],"callsign": [],"DepartureAirport": [],
        "ArrivalAirport": [],"Duration": []
        }

    for index,dz in dropzones_df.iterrows():
        icao = dz["dz_id"]
        name = dz["name"]
        print("Dropzone: ",name)

        departues = api.get_departures_by_airport(icao,int(yesterday_03.timestamp()),int(yesterday_23.timestamp())-1)

        for flight in departues or []:
            flight_history["date"].append(datetime.datetime.fromtimestamp(flight.firstSeen, TZ).strftime("%Y-%m-%d %H:%M:%S"))
            flight_history["icao24"].append(flight.icao24)
            flight_history["callsign"].append((flight.callsign or "").strip())
            flight_history["dropzone_id"].append(icao)
            flight_history["DepartureAirport"].append(icao)
            flight_history["ArrivalAirport"].append(flight.estArrivalAirport)
            flight_history["Duration"].append(flight.lastSeen - flight.firstSeen)

    return pd.DataFrame(flight_history)

       
def ingest_flight_history(flight_history: pd.DataFrame, connection):

    flight_history = flight_history.rename(columns={
        "date": "timestamp",
        "icao24": "icao24",
        "callsign": "callsign",
        "DepartureAirport": "departure_airport",
        "ArrivalAirport": "arrival_airport",
        "Duration": "duration",
    })

    if flight_history.empty:
        print("no flights yesterday")
        return

    upsert(connection, "flight_history", flight_history, ("dropzone_id", "timestamp", "icao24"))
    print(f"Loaded {len(flight_history):,} rows into flight_history.")

def main():
    url = URL.create(
        "postgresql+psycopg", host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)), database=os.environ["POSTGRES_DB"],
        username=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
    )
    engine = create_engine(url, connect_args={"connect_timeout": 10}, hide_parameters=True)
    try:
            # One transaction: either all rows are loaded or nothing changes
            with engine.begin() as connection:
                connection.execute(text("SET LOCAL lock_timeout = '10s'"))
                ingest_flight_history(load_flight_data(), connection)
    finally:    
            engine.dispose()

if __name__ == "__main__":
   main()
