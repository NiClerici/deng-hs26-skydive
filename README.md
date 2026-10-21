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
| Provider | [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (no API key) via `start_date` / `end_date`.| [Open-Meteo Forecast API](https://open-meteo.com/en/docs) (no API key) | [OpenSky Network API](https://openskynetwork.github.io/opensky-api/)|
| Purpose | Training: weather at the time of each flight | Input for the next 7 days prediction | Proxy for jump operations: jump aircraft repeatedly climbing and descending over a dropzone |
| Access / format | REST, JSON, hourly time series per lat/lon | REST, JSON, hourly time series per lat/lon | REST, JSON, `/flights/departure` per airfield; OAuth2 client credentials (`CLIENT_ID` / `CLIENT_SECRET`, see [`.env.example`](.env.example)); max. 2-day window per request, credit / rate limit |
| Variables | temperature 2 m, wind 10 m, gusts, wind at 850/700 hPa, cloud cover low, precipitation, visibility | same as historical | see schema |
| Schema | hourly: `date` + 8 float variables | same as historical | per flight: `icao24`, `callsign`, `firstSeen` / `lastSeen` (epoch), `estDepartureAirport` / `estArrivalAirport` |
| Update / history | one-off backfill 2026-01-01 to end of september | daily, 7 days ahead | daily |
| Volume | 6 dropzones x all of 2026 | small | 15 Departures per Day * all of 2026 |

Locations: [`data/swiss_dropzones.csv`](data/swiss_dropzones.csv), 6 Swiss dropzones (airfield ICAO code, coordinates, elevation).


## Risks
- Flights are only a proxy: a departure is not a jump, and no departure may mean no demand rather than bad weather.
- Weather data is model output, not measurement; coarse grid in the Alps.
- Identifying jump aircraft: OpenSky returns all departures (flight schools, private planes, rescue helicopters) and no longer provides aircraft types. We keep a list of known jump aircraft per dropzone ([`data/jump_aircraft.csv`](data/jump_aircraft.csv)); it currently covers only Bex and Reichenbach.
- Receiver coverage in Alpine valleys is incomplete, so some flights or parts of tracks are missing.
- API rate limits and access restrictions (OpenSky): the daily quota was already reached during testing, so the 2026 backfill has to be spread over several days.
- UTC vs local time when joining weather and flights.

## Planned stack
Python ingestion, Prefect (orchestration), Docker Compose, PostgreSQL (local); Terraform, GCS, BigQuery (final); classifier on weather features for the prediction.

## Getting started
1. `uv sync`
2. `cp .env.example .env` and add your OpenSky API client credentials
3. `uv run python script/<name>.py` (`meteo_past.py`, `meteo_forecast.py`, `flight_data.py`)

With Docker instead (PostgreSQL + ingestion container, needs the Postgres variables from `.env.example` in `.env`):
1. `docker compose -f storage/docker-compose.yml up -d postgres`
2. `docker compose -f storage/docker-compose.yml run --rm ingestion` runs both weather scripts; for another script append it, e.g. `... run --rm ingestion python script/flight_data.py`
3. Check the database: `docker compose -f storage/docker-compose.yml exec postgres psql -U skydive -d skydive`
4. Stop: `docker compose -f storage/docker-compose.yml down` (add `-v` to also delete the database volume)

## Orchestration
[Prefect](https://docs.prefect.io) schedules and runs the daily ingestion ([`daily_ingestion/flow.py`](daily_ingestion/flow.py)). It replaced the earlier plan to use Airflow: Prefect is plain Python (`@flow` / `@task`), needs no extra image or DAG folder, and covers scheduling, retries, reruns and backfills for our two daily jobs.

Start it (needs the Postgres and OpenSky variables from `.env.example` in `.env`):
```
docker compose -f storage/docker-compose.yml up -d --build postgres orchestrator daily_ingestion
```
The UI is at <http://localhost:4200> (Deployments).

| Deployment | Trigger | What it does |
|---|---|---|
| `daily-ingestion/daily` | cron `0 4 * * *` (04:00 UTC, i.e. 05:00 / 06:00 Zurich) | full refresh of the 7-day forecast, then the flights of the previous day |
| `backfill-flights/backfill` | manual, parameters `start` and `end` (YYYY-MM-DD) | loads the flights of every day in the range, one task per day |

- **Retries:** forecast 3x after 5 min, flights 3x after 15 min (OpenSky rate limit).
- **Rerun:** click *Run* on `daily` in the UI. The day is derived from the scheduled start time, so a rerun loads the same day again. Loads are upserts (`ON CONFLICT DO UPDATE`) in one transaction, so a rerun never creates duplicates.
- **Backfill:** *Run* -> *Custom run* on `backfill` in the UI, or
  ```
  docker compose -f storage/docker-compose.yml exec daily_ingestion \
    prefect deployment run 'backfill-flights/backfill' --param start=2026-10-15 --param end=2026-10-17
  ```
- **Verify:** after a run, `docker compose -f storage/docker-compose.yml exec postgres psql -U skydive -d skydive -c "SELECT date(timestamp), count(*) FROM flight_history GROUP BY 1 ORDER BY 1 DESC LIMIT 5;"` shows the loaded days. A second run of the same day leaves the counts unchanged.

Known limitations:
- Forecast and flights run one after the other in the same flow: if the forecast task fails for good, the flights of that day are not loaded until the flow is rerun.
- The historical weather backfill is not part of the orchestrator (`script/meteo_past.py`, run once by hand); the forecast is a full refresh and cannot be backfilled.
- A long flight backfill can hit the OpenSky quota; use short date ranges.
- Prefect stores its run history in SQLite (volume `prefect_data`), which is fine locally but not for production.

## Docs
- [Architecture v0.2 and division of responsibilities](docs/architecture.md)
- [Backlog](docs/backlog.md)

## Team
- Nico Clerici
- Jan Walker
