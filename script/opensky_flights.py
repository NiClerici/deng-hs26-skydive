"""Fetch departures from every dropzone in swiss_dropzones.csv via the OpenSky API.

    uv run --env-file .env python script/opensky_flights.py --start 2026-09-01 --end 2026-09-30

Without --start/--end it fetches the last 10 days up to yesterday (OpenSky only has data up to the previous day).
All departures go to data/raw/, the flights of the planes in data/jump_aircraft.csv to data/.
"""
import argparse
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
API_URL = "https://opensky-network.org/api/flights/departure"
DATA = Path(__file__).resolve().parent.parent / "data"
CHUNK = 2 * 24 * 3600  # OpenSky allows at most 2 days per request

session = requests.Session()


def login():
    r = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
    })
    r.raise_for_status()
    session.headers["Authorization"] = "Bearer " + r.json()["access_token"]


def departures(airport, begin, end):
    for _ in range(5):
        r = session.get(API_URL, params={"airport": airport, "begin": begin, "end": end})
        if r.status_code == 401:  # token expired (after 30 min)
            login()
        elif r.status_code == 429:
            time.sleep(int(r.headers.get("X-Rate-Limit-Retry-After-Seconds", 60)))
        elif r.status_code == 404:  # no flights
            return []
        else:
            r.raise_for_status()
            return r.json()
    raise RuntimeError(f"OpenSky keeps refusing {airport}, status {r.status_code}")


def main():
    yesterday = date.today() - timedelta(days=1)
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat, default=yesterday - timedelta(days=9))
    parser.add_argument("--end", type=date.fromisoformat, default=yesterday)
    args = parser.parse_args()

    start = int(pd.Timestamp(args.start, tz="UTC").timestamp())
    end = int(pd.Timestamp(args.end + timedelta(days=1), tz="UTC").timestamp())

    dropzones = pd.read_csv(DATA / "swiss_dropzones.csv")
    jump_aircraft = pd.read_csv(DATA / "jump_aircraft.csv", dtype=str)
    (DATA / "raw").mkdir(exist_ok=True)
    login()

    for dz in dropzones.itertuples():
        flights = []
        for begin in range(start, end, CHUNK):
            flights += departures(dz.dz_id, begin, min(begin + CHUNK, end))

        df = pd.DataFrame(flights, columns=["icao24", "callsign", "firstSeen", "lastSeen",
                                            "estDepartureAirport", "estArrivalAirport"])
        df = pd.DataFrame({
            "icao24": df["icao24"],
            "callsign": df["callsign"].str.strip(),
            "first_seen_utc": pd.to_datetime(df["firstSeen"], unit="s"),
            "last_seen_utc": pd.to_datetime(df["lastSeen"], unit="s"),
            "duration_min": ((df["lastSeen"] - df["firstSeen"]) / 60).round(1),
            "dep_airport": df["estDepartureAirport"],
            "arr_airport": df["estArrivalAirport"],
        }).sort_values("first_seen_utc")

        jumps = df[df["icao24"].isin(jump_aircraft.loc[jump_aircraft["dz_id"] == dz.dz_id, "icao24"])]

        filename = f"flights_{dz.dz_id.lower()}_{args.start}_{args.end}.csv"
        df.to_csv(DATA / "raw" / filename, index=False)
        jumps.to_csv(DATA / filename, index=False)
        print(f"{dz.dz_id}: {len(jumps)} of {len(df)} flights by jump planes -> {filename}")


if __name__ == "__main__":
    main()
