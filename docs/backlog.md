# Backlog

Owner in brackets, see [division of responsibilities](architecture.md#division-of-responsibilities). Both = done together.

**Pitch (W3)**
- [x] README, data sources, use case, Architecture v0.1 (Both)
- [x] Division of responsibilities (Both)
- [ ] Verify dropzone coordinates (Jan)
- [ ] Identify jump aircraft for LSZL, LSZO, LSZG, LSZK (Nico)

**Midterm (W7, submit by Thu 22.10.2026 15:30)**
- [ ] Ingestion scripts: weather, forecast (Jan), flights (Nico)
- [ ] Postgres schema + Docker Compose (Nico)
- [ ] Airflow DAG with backfill and retries (Jan)
- [ ] First transformation: join weather and flights (Both)
- [ ] Architecture v0.2, setup and verification steps (Both)

**Final (W14, submit by Thu 10.12.2026 20:00)**
- [ ] Terraform: GCS + BigQuery (Nico)
- [ ] Ingestion to GCS (Jan), transformation to BigQuery (Both)
- [ ] Table grain, partitioning, clustering (Both)
- [ ] Prediction model on weather features (Both)
- [ ] Data-quality checks (Jan), final architecture, limitations (Both)
