# Architecture v0.1

```mermaid
flowchart LR
    API[Open-Meteo API] --> ING[Python ingestion]
    SEED[dropzones.csv] --> ING
    ING --> RAW[(Raw: Postgres, later GCS)]
    RAW --> TRF[SQL transformation]
    TRF --> CUR[(Curated: Postgres, later BigQuery)]
    CUR --> USE[Analysis: jumpability per DZ]
    AF[Airflow in Docker Compose] -.schedules.-> ING
    AF -.schedules.-> TRF
    TF[Terraform] -.provisions.-> GCP[GCS bucket + BQ dataset]
```

## Ingestion strategy
- **Backfill:** one-off load from 2022 to today, then **incremental** daily load of the last day(s).
- **Granularity:** one API call per dropzone and date range.
- **Idempotent:** upsert on (dz_id, timestamp), so reruns are safe.
- **Failures:** Airflow retries with backoff; one failed dropzone does not block the others.
- **Cloud (final):** write raw JSON straight to GCS, without a local intermediate step.
