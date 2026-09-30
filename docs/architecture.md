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
- **Backfill:** one-off load from the start of 2026 to today, then **incremental** daily load of the last day(s). Forecast is a daily full refresh of the next 7 days.
- **Idempotent!**
