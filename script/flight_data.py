import os
import pandas as pd

from dotenv import load_dotenv
from opensky_api import OpenSkyApi
from datetime import datetime, timedelta, timezone

begin = datetime(2026,9,26,tzinfo=timezone.utc)
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
        day_end = min(day + timedelta(days=2),end)

        flight_data = {
            "date": [],"DZ_name":[],"icao24": [],"callsign": [],"DepartureAirport": [],
            "ArrivalAirport": [],"Duration": []
        }

        departures = api.get_departures_by_airport(AirportICAO, int(day.timestamp()), int(day_end.timestamp())-1)
        for  flight in departures or []:

            flight_data["date"].append(datetime.fromtimestamp(flight.firstSeen, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            flight_data["DZ_name"].append(dz_name)
            flight_data["icao24"].append(flight.icao24)
            flight_data["callsign"].append(flight.callsign.strip() or "")
            flight_data["DepartureAirport"].append(AirportICAO)
            flight_data["ArrivalAirport"].append(flight.estArrivalAirport)
            flight_data["Duration"].append(flight.lastSeen - flight.firstSeen)

        day = day_end

    pd.DataFrame(flight_data).to_csv("data/flights/flight_" + AirportICAO + "_" + dz_name.replace(" ", "_").lower() + "_" + begin.strftime("%Y-%m-%d") + "_" + end.strftime("%Y-%m-%d") + ".csv", index=False)

        
        
