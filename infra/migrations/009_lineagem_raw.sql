-- 009: campos de linhagem (rastreabilidade) em raw.job_observations
-- Adiciona ingested_at (momento da persistência) e scraper_version
-- (versão do coletor utilizado) para permitir rastrear qualquer registro
-- da Gold de volta à execução de coleta original.

ALTER TABLE raw.job_observations
    ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS scraper_version TEXT;

COMMENT ON COLUMN raw.job_observations.ingested_at IS
    'Momento da persistência no banco (ingestão), distinto de collected_at (coleta no portal).';
COMMENT ON COLUMN raw.job_observations.scraper_version IS
    'Versão do scraper utilizado na coleta (ex.: "1.0.0").';

-- Índice para consultas de linhagem por execução
CREATE INDEX IF NOT EXISTS ix_job_observations_run_id
    ON raw.job_observations (run_id);
