# Skydive Jumpability Pipeline

Batch pipeline that turns hourly weather data into a **"jumpable or not"** score per Swiss dropzone.

## Use case
- **Users:** skydivers and dropzone operators.
- **Question:** Given the weather forecast for next week, can we jump at the Dropzone? 
To answer this, we compare historical flight data (when jumps actually took place) with the weather at that time and get a prediction from it.
- **Data product:** Prediction for the next 7 days of whether it is possible to jump on a specific day or hour


## Data sources
| | Historical weather | Weather forecast | Flight data |
|---|---|---|---|
| Provider | [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (no API key) | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) (no API key) | [OpenSky Network API](https://openskynetwork.github.io/opensky-api/)|
| Purpose | Training: weather at the time of each flight | Input for the next 7 days prediction | Proxy for jump operations: jump aircraft repeatedly climbing and descending over a dropzone |
| Access / format | REST, JSON, hourly time series per lat/lon | REST, JSON, hourly time series per lat/lon | REST, JSON, aircraft state vectors / tracks |
| Variables | wind 10 m, gusts, wind at 850/700 hPa, cloud cover low, precipitation, visibility | same as historical | timestamp, position, altitude, aircraft type |
| Update / history | daily, scope: 2026 (Jan to today) | daily, 7 days ahead | daily, scope: 2026; history is available back to at least 2019 (tested) |
| Volume | 6 dropzones x all of 2026 | small | 15 Departures per Day * all of 2026 |

Locations: [`data/siwss_dropzones.csv`](data/swiss_dropzones.csv), 6 Swiss dropzones (coordinates approximate, to verify).


## Planned stack
Python ingestion, Apache Airflow, PostgreSQL (local).

## Docs
[Architecture v0.1](docs/architecture.md) | [Backlog](docs/backlog.md)

## Team
- Nico Clerici
- Jan Walker
