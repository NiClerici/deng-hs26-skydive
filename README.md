# Skydive Jumpability Pipeline

Batch pipeline that turns hourly weather data into a **"jumpable or not"** score per Swiss dropzone.

## Use case
- **Users:** skydivers and dropzone operators.
- **Question:** Given the weather forecast for next week, can we jump at the Dropzone? 
To answer this, we compare historical flight data (when jumps actually took place) with the weather at that time and get a prediction from it.
- **Label:** an hour counts as jumpable if at least one departure took place under similar weather in the historical data.
- **Data product:** Prediction for the next 7 days of whether it is possible to jump on a specific day or hour


## Data sources
| | Historical weather | Weather forecast | Flight data |
|---|---|---|---|
| Provider | [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (no API key). The current prototype uses the Forecast API with `past_days` (last ~3 months only); the 2026 backfill needs the Historical Forecast API | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) (no API key) | [OpenSky Network API](https://openskynetwork.github.io/opensky-api/), departures endpoint (`/flights/departure`) |
| Purpose | Training: weather at the time of each flight | Input for the next 7 days prediction | Proxy for jump operations: departures of known jump aircraft from a dropzone |
| Access / format | REST, JSON, hourly time series per lat/lon | REST, JSON, hourly time series per lat/lon | REST, JSON, list of departures per airfield (ICAO code); OAuth2 client credentials; max 2 days per request |
| Variables | wind 10 m, gusts, wind at 850/700 hPa, cloud cover low, precipitation, visibility | same as historical | aircraft ID (`icao24`), callsign, first/last seen (UTC), estimated departure/arrival airfield |
| Update / history | daily, scope: 2026 (Jan to today) | daily, 7 days ahead | updated nightly, so data only up to yesterday; scope: 2026; history is available back to at least 2019 (tested) |
| Volume | 6 dropzones x 24 h x all of 2026 (~40k rows) | 6 dropzones x 168 h per run | ~10 jump flights per day at Bex (measured 26–27 Sep 2026); all departures are much higher at busy airfields (Locarno ~60 per day) |

Locations: [`data/swiss_dropzones.csv`](data/swiss_dropzones.csv), 6 Swiss dropzones (coordinates approximate, to verify).


## Risks
- Flights are only a proxy: a departure is not a jump, and no departure may mean no demand rather than bad weather.
- Weather data is model output, not measurement; coarse grid in the Alps.
- Identifying jump aircraft: OpenSky returns all departures (flight schools, private planes, rescue helicopters) and no longer provides aircraft types. We keep a list of known jump aircraft per dropzone ([`data/jump_aircraft.csv`](data/jump_aircraft.csv)); it currently covers only Bex and Reichenbach.
- Receiver coverage in Alpine valleys is incomplete, so some flights or parts of tracks are missing.
- API rate limits and access restrictions (OpenSky): the daily quota was already reached during testing, so the 2026 backfill has to be spread over several days.
- UTC vs local time when joining weather and flights.

## Planned stack
Python ingestion, Apache Airflow, Docker Compose, PostgreSQL (local); Terraform, GCS, BigQuery (final); classifier on weather features for the prediction.

## Docs
- [Architecture v0.1 and division of responsibilities](docs/architecture.md)
- [Backlog](docs/backlog.md)

## Team
- Nico Clerici
- Jan Walker
