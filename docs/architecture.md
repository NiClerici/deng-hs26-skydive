# Architecture v0.1

```mermaid
flowchart LR
    HW[Open-Meteo Historical Forecast API] --> ING[Python ingestion]
    FC[Open-Meteo Forecast API] --> ING
    OS[OpenSky flights] --> ING
    SEED[swiss_dropzones.csv] --> ING
    ING --> RAW[(Raw: Postgres, later GCS)]
    RAW --> TRF[SQL transformation: weather + flights]
    TRF --> CUR[(Curated: Postgres, later BigQuery)]
    CUR --> MOD[Prediction: jumpable next 7 days]
    AF[Airflow in Docker Compose] -.schedules.-> ING
   
```


## Ingestion strategy
- **Weather backfill:** one-off load of Jan 2026 to today via Historical Forecast API. Afterwards a daily incremental load via `past_days`.
- **Forecast:** daily full refresh of the next 7 days.
- **Flights:** backfill in 2-day windows (API limit) per airfield, afterwards a daily incremental load.
- **Failure behaviour:** retries with backoff; reruns and backfills are safe because loads are idempotent.
