import argparse
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
API_URL = "https://opensky-network.org/api/flights/departure"
DATA = Path(__file__).resolve().parent.parent / "data"
CHUNK = timedelta(days=2)  # OpenSky allows at most 2 days per request
COLUMNS = ["date", "icao24", "callsign", "DepartureAirport", "ArrivalAirport", "Duration"]

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 9, 30))
    args = parser.parse_args()

    start = datetime.combine(args.start, datetime.min.time(), timezone.utc)
    end = datetime.combine(args.end + timedelta(days=1), datetime.min.time(), timezone.utc)

    load_dotenv()
    login()
    dropzones = pd.read_csv(DATA / "swiss_dropzones.csv")
    (DATA / "flights").mkdir(exist_ok=True)

    for dz in dropzones.itertuples():
        csv_path = DATA / "flights" / f"flight_{dz.dz_id}_{dz.name.replace(' ', '_').lower()}.csv"
        progress_path = DATA / "flights" / f".progress_{dz.dz_id}.txt"

        day = start
        if progress_path.exists():
            day = max(start, datetime.fromisoformat(progress_path.read_text().strip()))
        print(f"{dz.dz_id}: {day.date()} -> {args.end}")

        while day < end:
            day_end = min(day + CHUNK, end)
            flights = departures(dz.dz_id, int(day.timestamp()), int(day_end.timestamp()) - 1)

            df = pd.DataFrame({
                "date": [datetime.fromtimestamp(f["firstSeen"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S") for f in flights],
                "icao24": [f["icao24"] for f in flights],
                "callsign": [(f["callsign"] or "").strip() for f in flights],
                "DepartureAirport": dz.dz_id,
                "ArrivalAirport": [f["estArrivalAirport"] for f in flights],
                "Duration": [f["lastSeen"] - f["firstSeen"] for f in flights],
            }, columns=COLUMNS)
            if len(df):
                df.to_csv(csv_path, mode="a", index=False, header=not csv_path.exists())

            print(f"  {dz.dz_id} {day.date()} -> {day_end.date()}: {len(df)} flights", flush=True)

            # only written after a successful request, so a rerun resumes here
            progress_path.write_text(day_end.isoformat())
            day = day_end


if __name__ == "__main__":
    main()
