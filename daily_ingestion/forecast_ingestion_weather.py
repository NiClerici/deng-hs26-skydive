from datetime import date
from pathlib import Path
from sqlalchemy import URL, create_engine, text

import os
import openmeteo_requests as omr
import pandas as pd


openmeteo = omr.Client()

url = "https://api.open-meteo.com/v1/forecast"

DROPZONES_CSV = Path(__file__).resolve().parent.parent / "data" / "swiss_dropzones.csv"

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

def get_weather():
    dropzones_df = pd.read_csv(DROPZONES_CSV, usecols=["dz_id", "name", "lat", "lon"])
    weather_forecast = []

    for index, row in dropzones_df.iterrows():
        print(f"Dropzone: {row['name']} ({row['lat']}, {row['lon']})")
        params = {
            "latitude": row['lat'],
            "longitude": row['lon'],
            "hourly":  ["temperature_2m", "wind_speed_10m", "wind_gusts_10m", "cloud_cover_low", "precipitation", "visibility", "wind_speed_850hPa", "wind_speed_700hPa"],
            "timezone": "Europe/Zurich",
        }

        responses = openmeteo.weather_api(url, params=params)

        response = responses[0]
        print(f"Coord.: {response.Latitude()}°N {response.Longitude()}°E")

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_wind_speed_10m = hourly.Variables(1).ValuesAsNumpy()
        hourly_wind_gusts_10m = hourly.Variables(2).ValuesAsNumpy()
        hourly_cloud_cover_low = hourly.Variables(3).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(4).ValuesAsNumpy()
        hourly_visibility = hourly.Variables(5).ValuesAsNumpy()
        hourly_wind_speed_850hPa = hourly.Variables(6).ValuesAsNumpy()
        hourly_wind_speed_700hPa = hourly.Variables(7).ValuesAsNumpy()

        hourly_data = {
            "date": pd.date_range(
                start = pd.to_datetime(hourly.Time(),unit='s', utc=True),
                end = pd.to_datetime(hourly.TimeEnd(),unit='s', utc=True) ,
                freq = pd.Timedelta(seconds=hourly.Interval()),
                inclusive = "left"
                )
        }

        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
        hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
        hourly_data["cloud_cover_low"] = hourly_cloud_cover_low
        hourly_data["precipitation"] = hourly_precipitation
        hourly_data["visibility"] = hourly_visibility
        hourly_data["wind_speed_850hPa"] = hourly_wind_speed_850hPa
        hourly_data["wind_speed_700hPa"] = hourly_wind_speed_700hPa
        hourly_data["dropzone_id"] = row['dz_id']

        hourly_dataframe = pd.DataFrame(data=hourly_data)
        hourly_dataframe["date"] = hourly_dataframe["date"].dt.tz_convert("Europe/Zurich").dt.tz_localize(None)
        weather_forecast.append(hourly_dataframe)
        print(hourly_dataframe.head())

    return pd.concat(weather_forecast, ignore_index=True)

def ingest_weather_forecast(weather_forecast: pd.DataFrame,connection):
    weather_forecast = weather_forecast.rename(columns={
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
    if weather_forecast.empty:
            raise RuntimeError("no weather forecast data == we gonna die")

    connection.execute(text("DELETE FROM public.weather_forecast"))
    upsert(connection, "weather_forecast", weather_forecast, ("dropzone_id", "timestamp"))
    print(f"Loaded {len(weather_forecast):,} rows into weather_forecast.")

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
                 ingest_weather_forecast(get_weather(), connection)
     finally:    
             engine.dispose()

if __name__ == "__main__":
   main()
