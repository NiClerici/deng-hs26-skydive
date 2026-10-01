import os
import pandas as pd

from dotenv import load_dotenv
from opensky_api import OpenSkyApi
from datetime import datetime, timedelta, timezone

begin = datetime(2026,1,1,tzinfo=timezone.utc)
end = datetime(2026,9,29,tzinfo=timezone.utc)

load_dotenv()

api = OpenSkyApi(client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET"))

dropzones = pd.read_csv("data/swiss_dropzones.csv", usecols=["dz_id", "name", "lat", "lon"])

for index, row in dropzones.iterrows():
    AirportICAO = row['dz_id']
    dz_name = row['name']
    print(f"Dropzone: {AirportICAO}, Name: {dz_name}")

    csv_path = f"data/flights/flight_{AirportICAO}_{dz_name.replace(' ', '_').lower()}.csv"
    progress_path = f"data/flights/.progress_{AirportICAO}.txt"

    #max 2tage pro abfrage erlaubt und wiederaufnahme der letzten abfrage
    day = begin
    if os.path.exists(progress_path):
        with open(progress_path) as f:
            day = max(begin,datetime.fromisoformat(f.read().strip()))

    flight_data = {
        "date": [],"DZ_name":[],"icao24": [],"callsign": [],"DepartureAirport": [],
        "ArrivalAirport": [],"Duration": []
        }

    stop = False

    while day < end:

        day_end = min(day + timedelta(days=2),end)

        try:
            departures = api.get_departures_by_airport(AirportICAO, int(day.timestamp()), int(day_end.timestamp())-1)
        except Exception as e:
            print(f" Abbruch bei {day.date()}: {e}")
            stop = True
            break

        for  flight in departures or []:

            flight_data["date"].append(datetime.fromtimestamp(flight.firstSeen, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            flight_data["DZ_name"].append(dz_name)
            flight_data["icao24"].append(flight.icao24)
            flight_data["callsign"].append((flight.callsign or "").strip())
            flight_data["DepartureAirport"].append(AirportICAO)
            flight_data["ArrivalAirport"].append(flight.estArrivalAirport)
            flight_data["Duration"].append(flight.lastSeen - flight.firstSeen)

        if flight_data["date"]:
            pd.DataFrame(flight_data).to_csv(csv_path,mode="a",index=False,header=not os.path.exists(csv_path))

        flight_data = {k: [] for k in flight_data}

        with open(progress_path, "w") as f:
            f.write(day_end.isoformat())
        
        day = day_end

    if stop:
        break
