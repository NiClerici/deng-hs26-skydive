# Skydive Jumpability Pipeline

Batch pipeline that turns hourly weather data into a **"jumpable or not"** score per Swiss dropzone.

## Use case
- **Users:** skydivers and dropzone operators.
- **Question:** when (month, hour) and where is it typically jumpable, and how did a given day score?
- **Data product:** `fct_jumpability_hourly` with one row per dropzone and hour (score, `is_jumpable`, limiting factor), plus a daily/monthly aggregate per dropzone.

## Data source
| | |
|---|---|
| Provider | [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (no API key) |
| Access / format | REST, JSON, hourly time series per lat/lon |
| Variables | wind 10 m, gusts, wind at 850/700 hPa, cloud cover low, precipitation, visibility |
| Update / history | daily, from 2022 |
| Volume | 6 dropzones x 24 h x 365 d is about 53k rows/year, small |
| Locations | [`data/dropzones.csv`](data/dropzones.csv), 6 Swiss dropzones (coordinates approximate, to verify) |
| Risks | model data, not measurements; coarse grid in the Alps; missing values; API rate limits; UTC vs local time |

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
