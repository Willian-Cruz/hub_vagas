-- Histórico bruto das coletas. Idempotente e compatível com os modelos SQLAlchemy.
CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.scrape_runs (
    run_id UUID NOT NULL,
    source VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL,
    pages_processed INTEGER NOT NULL DEFAULT 0,
    jobs_found INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_bronze_scrape_runs PRIMARY KEY (run_id, source)
);

CREATE TABLE IF NOT EXISTS bronze.job_observations (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    source VARCHAR(80) NOT NULL,
    source_job_id VARCHAR(1000) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_hash VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    CONSTRAINT uq_bronze_observation_run_source_job
        UNIQUE (run_id, source, source_job_id),
    CONSTRAINT fk_bronze_observation_run
        FOREIGN KEY (run_id, source)
        REFERENCES bronze.scrape_runs (run_id, source)
);

CREATE INDEX IF NOT EXISTS ix_bronze_observations_source_collected_at
    ON bronze.job_observations (source, collected_at);

CREATE INDEX IF NOT EXISTS ix_bronze_observations_source_job_id
    ON bronze.job_observations (source, source_job_id);
