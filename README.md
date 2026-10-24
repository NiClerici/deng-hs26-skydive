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

## Transformation
Two SQL views turn the loaded tables into the midterm data product: for every hour of the 7-day forecast, **is the weather inside the range in which jump aircraft actually flew?** They are plain SQL in `storage/sql/`, are not created automatically and are applied in [instruction.md](docs/instruction.md), step 7.

| View (file) | Reads | One row | Purpose |
|---|---|---|---|
| `jumpability_range` ([`get_jumpability_range.sql`](storage/sql/get_jumpability_range.sql)) | `flight_history`, `jump_aircraft`, `weather_history` | the whole dataset (one row) | The weather limits (temperature, wind, gusts, low cloud, rain, visibility, wind at 850 / 700 hPa) under which jump flights took place |
| `jumpable_time` ([`get_jumpable_time.sql`](storage/sql/get_jumpable_time.sql)) | `weather_forecast`, `jumpability_range` | dropzone x forecast hour (UTC) | Per-variable flags (`temp_ok`, `wind_ok`, ...) and `jumpable` = all flags true |

Why each step is there:

| Step | Reason |
|---|---|
| Only known jump aircraft of that dropzone (`icao24` + dropzone) that land where they took off | OpenSky returns every departure (flight school, private, rescue). Flights that land elsewhere are repositioning flights, not jump sorties. |
| Flight durations outside the IQR fences (Q1 - 1.5 IQR, Q3 + 1.5 IQR) are dropped, per dropzone | Removes cross-country and sightseeing flights. Per dropzone, because a sortie at Bex (median about 29 min) is not comparable with one at Reichenbach (about 16 min). |
| Every flight hour counts once | Hours with many departures must not weigh more than others. |
| Flight time (UTC) converted to Europe/Zurich before joining the weather | `weather_history` holds Zurich wall-clock time, the backfilled `flight_history` holds UTC. Joined as stored, every flight would be matched to the weather 1 to 2 hours off. |
| Limits are the 5th and 95th percentile of the remaining flight hours, not min and max | One flight in a storm would otherwise widen the range until nothing is ruled out. The columns keep their `min_` / `max_` names. |
| In `jumpable_time` only the bad direction excludes an hour (wind, gusts, low cloud, rain, wind aloft above the limit, visibility below it); temperature is checked on both sides | Calm air and good visibility are never a reason to say no. |
| `jumpability_range` is joined to every forecast hour with `CROSS JOIN` | It has exactly one row. |

`get_callsigns.sql` and `get_jump_aircraft_duration_range.sql` are analysis queries, not part of the pipeline: they were used to find jump-aircraft candidates for `data/jump_aircraft.csv`.

Known limitations of the transformation:
- **Rule, not a model.** the transformation checks only the hourly forecast so there could be some strong switches from the weather characteristics during that time that could lead to wrong data.
- **One global range** for all dropzones, and no daylight check, so night hours can come out as jumpable.
- **Only Bex and Reichenbach are reliable.** `jump_aircraft.csv` has one unverified aircraft each for LSZG, LSZK, LSZL and LSZO, so the range rests on LSGB and LSGR (704 and 708 flights; 19 to 20 for LSZG and LSZL, none for LSZK and LSZO).

## Orchestration
[Prefect](https://docs.prefect.io) schedules and runs the daily ingestion ([`daily_ingestion/flow.py`](daily_ingestion/flow.py)). It replaced the earlier plan to use Airflow: Prefect is plain Python (`@flow` / `@task`), needs no extra image or DAG folder, and covers scheduling, retries, reruns and backfills for our two daily jobs.

Start it (needs the Postgres and OpenSky variables from `.env.example` in `.env`):
```
docker compose -f storage/docker-compose.yml up -d --build postgres orchestrator daily_ingestion pgadmin
```
The UI is at <http://localhost:4200> (Deployments). pgAdmin to browse the database is at <http://localhost:5050> (login from `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` in `.env`, the `skydive` server is pre-registered). Full run and verification steps: [instruction.md](docs/instruction.md).

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
- The history CSVs are loaded into Postgres by hand (`storage/scripts/weather_history_data_ingest.py`, `flight_history_data_ingest.py`, see [instruction.md](docs/instruction.md), step 4); the flows only load the forecast and new flights.
- If OpenSky rejects the credentials (`401`) the flights task fails after its retries, but the forecast of that run is already stored.
- A long flight backfill can hit the OpenSky quota; use short date ranges.
- Prefect stores its run history in SQLite (volume `prefect_data`), which is fine locally but not for production.

## Docs
- [Instructions: run and verify the local pipeline](docs/instruction.md)
- [Architecture v0.2 and division of responsibilities](docs/architecture.md)
- [Backlog](docs/backlog.md)

## Team
- Nico Clerici
- Jan Walker
