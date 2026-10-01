import os
import pandas as pd

from dotenv import load_dotenv
from opensky_api import OpenSkyApi
from datetime import datetime, timedelta, timezone

begin = datetime(2026,9,21,tzinfo=timezone.utc)
end = datetime(2026,9,28,tzinfo=timezone.utc)

load_dotenv()

api = OpenSkyApi(client_id=os.getenv("CLIENT_ID"), client_secret=os.getenv("CLIENT_SECRET"))

dropzones = pd.read_csv("data/swiss_dropzones.csv", usecols=["dz_id", "name", "lat", "lon"])

for index, row in dropzones.iterrows():

    #max 2tage pro abfrage erlaubt
    day = begin

    AirportICAO = row['dz_id']
    dz_name = row['name']
    print(f"Dropzone: {AirportICAO}, Name: {dz_name}")

    while day < end:
        day_end = min(day + timedelta(days=1),end)

        departures = api.get_departures_by_airport(AirportICAO, int(day.timestamp()), int(day_end.timestamp()))
        arrivals = api.get_arrivals_by_airport(AirportICAO,int(day.timestamp()), int(day_end.timestamp()))
        print(departures)
        for  flight in departures or []:
            print(flight)
        day = day_end

