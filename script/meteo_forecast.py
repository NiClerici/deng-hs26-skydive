import openmeteo_requests as omr
import pandas as pd

openmeteo = omr.Client()

url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 46.25,
    "longitude": 6.98,
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

hourly_dataframe = pd.DataFrame(data=hourly_data)
hourly_dataframe["date"] = hourly_dataframe["date"].dt.tz_convert("Europe/Zurich")
hourly_dataframe.head(10).to_csv("data/forecast_lsgb_next7d.csv", index=False)
print("Hourly Data: ",hourly_dataframe)