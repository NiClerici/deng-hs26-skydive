from datetime import date, timedelta
from zoneinfo import ZoneInfo

from prefect import flow, task, serve
from prefect.runtime import flow_run

import daily_ingestion_flight as flights
import forecast_ingestion_weather as weather

TZ = ZoneInfo("Europe/Zurich")

@task(retries=3, retry_delay_seconds=300)
def ingest_weather_forecast():
    weather.main()

@task(retries=3, retry_delay_seconds=900)
def ingest_flights(day: date):
    flights.main(day)

@flow(log_prints=True)
def daily_ingestion(day: date | None = None):
    if day is None:
        day = flow_run.scheduled_start_time.astimezone(TZ).date() - timedelta(days=1)
    ingest_weather_forecast()
    ingest_flights(day)


@flow(log_prints=True)
def backfill_flights(start: date, end: date):
    day = start
    while day <= end:
        ingest_flights(day)
        day += timedelta(days=1)

if __name__ == "__main__":
    serve(
        daily_ingestion.to_deployment(name="daily", cron="0 4 * * *"), 
        backfill_flights.to_deployment(name="backfill"), 

    )