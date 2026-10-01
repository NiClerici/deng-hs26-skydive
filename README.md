# Skydive Jumpability Pipeline

Batch pipeline that turns hourly weather data into a **"jumpable or not"** score per Swiss dropzone.

## Use case
- **Users:** skydivers and dropzone operators.
- **Question:** Given the weather forecast for next week, can we jump at the Dropzone? 
To answer this, we compare historical flight data (when jumps actually took place) with the weather at that time and get a prediction from it.
- **Grain:** one row = one dropzone x one hour (UTC).
- **Label:** `jumpable = 1` if at least one jump aircraft of that dropzone departed in that hour, else `0`. 
- **Features:** weather of the same dropzone and hour.
- **Data product:** probability of `jumpable` per dropzone and hour for the next 7 days, also aggregated per day.


## Data sources
| | Historical weather | Weather forecast | Flight data |
|---|---|---|---|
| Provider | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) with `past_days` for the daily incremental load; one-off backfill (Jan 2026 to today) via [Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (no API key) | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) (no API key) | [OpenSky Network API](https://openskynetwork.github.io/opensky-api/)|
| Purpose | Training: weather at the time of each flight | Input for the next 7 days prediction | Proxy for jump operations: jump aircraft repeatedly climbing and descending over a dropzone |
| Access / format | REST, JSON, hourly time series per lat/lon | REST, JSON, hourly time series per lat/lon | REST, JSON, `/flights/departure` per airfield; OAuth2 client credentials (`CLIENT_ID` / `CLIENT_SECRET`, see [`.env.example`](.env.example)); max. 2-day window per request, credit / rate limit |
| Variables | temperature 2 m, wind 10 m, gusts, wind at 850/700 hPa, cloud cover low, precipitation, visibility | same as historical | see schema |
| Schema | hourly: `date` + 8 float variables | same as historical | per flight: `icao24`, `callsign`, `firstSeen` / `lastSeen` (epoch), `estDepartureAirport` / `estArrivalAirport` |
| Update / history | daily, scope: 2026 (Jan to today) | daily, 7 days ahead | daily, scope: 2026; history is available back to at least 2019 (tested) |
| Volume | 6 dropzones x all of 2026 | small | 15 Departures per Day * all of 2026 |

Locations: [`data/swiss_dropzones.csv`](data/swiss_dropzones.csv), 6 Swiss dropzones (airfield ICAO code, coordinates, elevation).


## Risks
- Flights are only a proxy: a departure is not a jump, and no departure may mean no demand rather than bad weather.
- Weather data is model output, not measurement; coarse grid in the Alps.
- API rate limits and access restrictions (OpenSky).
- UTC vs local time when joining weather and flights.

## Planned stack
Python ingestion, Apache Airflow, Docker Compose, PostgreSQL (local); Terraform, GCS, BigQuery (final); classifier on weather features for the prediction.

## Getting started
1. `uv sync`
2. `cp .env.example .env` and add your OpenSky API client credentials
3. `uv run python script/<name>.py` (`meteo_past.py`, `meteo_forecast.py`, `flight_data.py`)

## Docs
- [Architecture v0.1](docs/architecture.md)
- [Backlog](docs/backlog.md)

## Team
- Nico Clerici
- Jan Walker
