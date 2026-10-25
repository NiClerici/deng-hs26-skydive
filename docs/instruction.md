# Instructions: run and verify the local pipeline

Run all commands from the repo root. Requires Docker.

## 1. Setup
```
cp .env.example .env
```
Fill in `CLIENT_ID` / `CLIENT_SECRET` (OpenSky) and the `POSTGRES_*` values (use `skydive` for user and database; the commands below assume it).

## 2. Start the stack
```
docker compose -f storage/docker-compose.yml up -d --build postgres orchestrator daily_ingestion pgadmin
docker compose -f storage/docker-compose.yml ps
```
Expected: `postgres` and `orchestrator` are `healthy`, `daily_ingestion` and `pgadmin` are `Up`. On the first start Postgres creates the tables from `storage/sql/schema.sql`.

pgAdmin (optional, to browse the tables and views) is at <http://localhost:5050>. Log in with `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` from `.env`; the `skydive` server is pre-registered, its password is `POSTGRES_PASSWORD`.

## 3. Load the seed data (once)
```
docker compose -f storage/docker-compose.yml run --rm ingestion python storage/scripts/manual_data_ingest.py
```
Expected: `Loaded 6 rows into swiss_dropzone.` and a row count for `jump_aircraft`. Without this step the daily run fails on a foreign key (`dropzone_id` not in `swiss_dropzone`).

## 4. Load the history (once)
The history CSVs are committed (`data/past`: weather, `data/flights`: flights), so this step needs no OpenSky or Open-Meteo access. Run it after step 3, the tables reference `swiss_dropzone`.
```
docker compose -f storage/docker-compose.yml run --rm ingestion python storage/scripts/weather_history_data_ingest.py
docker compose -f storage/docker-compose.yml run --rm ingestion python storage/scripts/flight_history_data_ingest.py
```
Expected: `Loaded 6,528 rows into weather_history.` once per weather file (12 lines) and one `Loaded ... rows into flight_history.` line per dropzone (6 lines, 17,309 rows in total). Both commands can be rerun (upserts).

The CSVs can be recreated with `script/meteo_past.py` and `script/flight_data.py`; `flight_data.py` needs the OpenSky credentials and takes days because of the quota.

## 5. Run the pipeline
Open the Prefect UI at <http://localhost:4200> -> **Deployments** -> `daily-ingestion/daily` -> **Run** -> **Quick run**.

Expected: state **Completed**, with logs `Loaded ... rows into weather_forecast` and `... into flight_history`.

If the flights task fails with `401 Unauthorized`, OpenSky rejected `CLIENT_ID` / `CLIENT_SECRET` in `.env`. The forecast of that run is already stored (it runs first) and the history from step 4 is unaffected, so you can continue with step 6 and 7. After fixing `.env`, recreate the runner (`docker compose -f storage/docker-compose.yml up -d --force-recreate daily_ingestion`) and run `daily` again.

## 6. Check the data
```
docker compose -f storage/docker-compose.yml exec postgres psql -U skydive -d skydive \
  -c "SELECT count(*) FROM weather_history;" \
  -c "SELECT count(*) FROM flight_history;" \
  -c "SELECT dropzone_id, count(*), min(timestamp), max(timestamp) FROM weather_forecast GROUP BY 1 ORDER BY 1;" \
  -c "SELECT date(timestamp), count(*) FROM flight_history GROUP BY 1 ORDER BY 1 DESC LIMIT 5;"
```
Expected: `weather_history` 39,168 rows (6 dropzones x 6,528 hours); `flight_history` 17,309 rows plus the days loaded by the daily flow; `weather_forecast` about 167 hours per dropzone for the next 7 days.

## 7. Create and check the transformation views
The views are not created automatically. Apply them in this order (`jumpable_time` reads `jumpability_range`); both files can be rerun. Why they are built this way: [README, Transformation](../README.md#transformation).
```
cat storage/sql/get_jumpability_range.sql | docker compose -f storage/docker-compose.yml exec -T postgres psql -U skydive -d skydive
cat storage/sql/get_jumpable_time.sql | docker compose -f storage/docker-compose.yml exec -T postgres psql -U skydive -d skydive
```
Expected: `CREATE VIEW` for both (the second file prints `DROP VIEW` first on a rerun). Check:
```
docker compose -f storage/docker-compose.yml exec postgres psql -U skydive -d skydive -x \
  -c "SELECT * FROM jumpability_range;"
docker compose -f storage/docker-compose.yml exec postgres psql -U skydive -d skydive \
  -c "SELECT dropzone_id, count(*) AS hours, count(*) FILTER (WHERE jumpable) AS jumpable_hours FROM jumpable_time GROUP BY 1 ORDER BY 1;"
```
Expected:
- `jumpability_range`: one row. On the committed history (before any daily flight load) roughly `min_temp` 3.5, `max_temp` 30.0, `max_wind` 13.3, `max_gust` 25.6, `max_cloud_low` 63, `max_precip` 0, `min_visibility` 21,955, `max_wind_850` 19.5, `max_wind_700` 48.0. Wind is km/h, see the README limitations.
- `jumpable_time`: one row per dropzone and forecast hour (about 167 per dropzone, 1,002 in total). `jumpable_hours` depends on the forecast of the day; it is between 0 and `hours`, normally clearly below `hours`.

## 8. Rerun
Start `daily-ingestion/daily` again. The state is **Completed** and the row counts from step 6 stay the same (flights are upserts, the forecast is deleted and reloaded in one transaction, so it always holds only the current 7 days); `jumpable_time` follows the new forecast without a rerun of step 7, it is a view.

## 9. Backfill
UI: `backfill-flights/backfill` -> **Run** -> **Custom run** with `start` and `end` (YYYY-MM-DD). Or:
```
docker compose -f storage/docker-compose.yml exec daily_ingestion \
  prefect deployment run 'backfill-flights/backfill' --param start=2026-10-18 --param end=2026-10-19
```
Expected: one task run per day. Rerun step 6 to see the added days. Keep ranges short (OpenSky quota).

## 10. Retry (optional)
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
| `column "callsign_id" of relation "jump_aircraft" does not exist` | The volume was created with an older `schema.sql`. Recreate it as in the line above `relation ... does not exist` (the history is reloaded from the committed CSVs in step 4) |
| `relation "jumpability_range"` or `"jumpable_time" does not exist` | The views are not created automatically, do step 7 |
| `jumpable_time` or `jumpability_range` is empty / NULL | `weather_forecast` (step 5) or the history (step 4) is empty |
| Flights task fails with `401 Unauthorized` | Invalid OpenSky credentials in `.env`, see step 5 |
| `ModuleNotFoundError` / file not found for a script in `ingestion` | The `ingestion` image is old: `docker compose -f storage/docker-compose.yml build ingestion` |
| Deployments missing in the UI | Check `docker compose -f storage/docker-compose.yml logs daily_ingestion` |
