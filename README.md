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
| Provider | [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (no API key) | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) (no API key) | [OpenSky Network API](https://openskynetwork.github.io/opensky-api/) (free account); alternatives: ADS-B Exchange, Flightradar24 (paid), dropzone logs on request |
| Purpose | Training: weather at the time of each flight | Input for the next 7 days prediction | Proxy for jump operations: jump aircraft repeatedly climbing and descending over a dropzone |
| Access / format | REST, JSON, hourly time series per lat/lon | REST, JSON, hourly time series per lat/lon | REST, JSON, aircraft state vectors / tracks |
| Variables | wind 10 m, gusts, wind at 850/700 hPa, cloud cover low, precipitation, visibility | same as historical | timestamp, position, altitude, aircraft type |
| Update / history | daily, scope: 2026 (Jan to today) | daily, 7 days ahead | daily, scope: 2026; history is available back to at least 2019 (tested) |
| Volume | 6 dropzones x 24 h x about 270 d is about 39k rows | small | about 30k departures (estimate); about 25k credits for the backfill at 30 credits per call, roughly 7 days at 4,000 credits/day |

Use the Historical *Forecast* API (not Archive/ERA5) for training, so the model learns from forecast data like it will see in production.

Locations: [`data/dropzones.csv`](data/dropzones.csv), 6 Swiss dropzones (coordinates approximate, to verify).

**Risks**
- Weather: model data, not measurements; coarse grid in the Alps; missing values; API rate limits; UTC vs local time.
- Flight data: no official jump data exists; ADS-B coverage in the Alps can be patchy and the aircraft-based proxy is not an exact jump count. This is the biggest project risk, check OpenSky data for the 6 dropzones first.
- Optional cross-check: [MeteoSwiss Open Data](https://www.meteoswiss.admin.ch/services-and-publications/service/open-data.html) (real measurements, but stations are not at the dropzones).

## Jumpability rules v0 (configurable)
Jumpable if ground wind < 15 kn, gusts < 20 kn, wind at 700 hPa < 35 kn, low cloud < 50 %, precipitation = 0 and visibility > 5 km. Thresholds are placeholders to be refined.

## Planned stack
Python ingestion, Apache Airflow, PostgreSQL (local), Docker Compose, Terraform, GCS + BigQuery (final).

## Docs
[Architecture v0.1](docs/architecture.md) | [Backlog](docs/backlog.md)

## Team
- Nico Clerici: ingestion, Airflow, Docker
- TBD: transformation, Terraform, BigQuery
- Both: documentation, data quality
