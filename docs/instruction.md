# Instructions: run and verify the local pipeline

Run all commands from the repo root. Requires Docker.

## 1. Setup
```
cp .env.example .env
```
Fill in `CLIENT_ID` / `CLIENT_SECRET` (OpenSky) and the `POSTGRES_*` values (use `skydive` for user and database; the commands below assume it).

## 2. Start the stack
```
docker compose -f storage/docker-compose.yml up -d --build postgres orchestrator daily_ingestion
docker compose -f storage/docker-compose.yml ps
```
Expected: `postgres` and `orchestrator` are `healthy`, `daily_ingestion` is `Up`. On the first start Postgres creates the tables from `storage/sql/schema.sql`.

## 3. Load the seed data (once)
```
docker compose -f storage/docker-compose.yml run --rm ingestion python storage/scripts/manual_data_ingest.py
```
Expected: `Loaded 6 rows into swiss_dropzone.` and a row count for `jump_aircraft`. Without this step the daily run fails on a foreign key (`dropzone_id` not in `swiss_dropzone`).

## 4. Run the pipeline
Open the Prefect UI at <http://localhost:4200> -> **Deployments** -> `daily-ingestion/daily` -> **Run** -> **Quick run**.

Expected: state **Completed**, with logs `Loaded ... rows into weather_forecast` and `... into flight_history`.

## 5. Check the data
```
docker compose -f storage/docker-compose.yml exec postgres psql -U skydive -d skydive \
  -c "SELECT count(*) FROM weather_forecast;" \
  -c "SELECT date(timestamp), count(*) FROM flight_history GROUP BY 1 ORDER BY 1 DESC LIMIT 5;"
```

## 6. Rerun
Start `daily-ingestion/daily` again. The state is **Completed** and the row counts from step 5 stay the same (loads are upserts).

## 7. Backfill
UI: `backfill-flights/backfill` -> **Run** -> **Custom run** with `start` and `end` (YYYY-MM-DD). Or:
```
docker compose -f storage/docker-compose.yml exec daily_ingestion \
  prefect deployment run 'backfill-flights/backfill' --param start=2026-10-18 --param end=2026-10-19
```
Expected: one task run per day. Rerun step 5 to see the added days. Keep ranges short (OpenSky quota).

## 8. Retry (optional)
```
docker compose -f storage/docker-compose.yml stop postgres
```
Start `daily` in the UI. The task fails and the log shows `Retry 1/3 will start 300 second(s) from now`. Then:
```
docker compose -f storage/docker-compose.yml start postgres
```

## Stop
```
docker compose -f storage/docker-compose.yml down
```
Do not add `-v` unless you want to delete the database.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `postgres` exits, `POSTGRES_PASSWORD is not specified` | `POSTGRES_*` is missing in `.env` |
| `relation ... does not exist` | The database was created without the schema. Run `down`, `docker volume rm skydive_pgdata`, then start again |
| `ForeignKeyViolation ... swiss_dropzone` | Seed data not loaded, do step 3 |
| Deployments missing in the UI | Check `docker compose -f storage/docker-compose.yml logs daily_ingestion` |
