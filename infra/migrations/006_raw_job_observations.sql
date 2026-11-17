-- 006: tabela append-only de observações brutas (raw.job_observations).
--
-- Rode UMA vez no banco hub_vagas, depois de um backup (pg_dump). É idempotente:
-- rodar de novo não altera nada que já foi criado.
--
-- O que faz:
--   1. cria o schema `raw`;
--   2. cria a tabela `raw.job_observations` com o payload bruto (JSONB) de cada
--      observação coletada, o hash do payload (dedup) e a flag de relevância;
--   3. cria o índice (source, source_job_id, collected_at desc) para dedup e
--      consulta da última observação de cada vaga no portal.
--
-- A tabela pública `public.jobs` é mantida como legado durante a transição e
-- não é mais gravada pelo Python; o dbt lê de `raw.job_observations` a partir
-- desta migração (P3).

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.job_observations (
    id                BIGSERIAL      PRIMARY KEY,
    run_id            UUID           NOT NULL,
    source            TEXT           NOT NULL,
    source_job_id     TEXT,                                     -- id_externo (pode ser NULL)
    collected_at      TIMESTAMPTZ    NOT NULL,
    payload_hash      TEXT           NOT NULL,
    raw_payload       JSONB          NOT NULL,
    is_relevant       BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_job_observations_source_job_collected
    ON raw.job_observations (source, source_job_id, collected_at DESC);

CREATE INDEX IF NOT EXISTS ix_job_observations_payload_hash
    ON raw.job_observations (payload_hash);

-- Comentários de documentação
COMMENT ON TABLE raw.job_observations IS
    'Observações brutas (append-only) coletadas pelos scrapers. Uma linha por '
    'coleta de cada vaga; o dbt deriva a camada Silver a partir dela.';
COMMENT ON COLUMN raw.job_observations.source IS 'Origem/portal (Vagas.com, InfoJobs, Gupy, Catho).';
COMMENT ON COLUMN raw.job_observations.source_job_id IS 'ID da vaga no portal (id_externo), quando disponível.';
COMMENT ON COLUMN raw.job_observations.collected_at IS 'Momento da coleta.';
COMMENT ON COLUMN raw.job_observations.payload_hash IS 'SHA-256 do raw_payload (dedup de retransmissão idêntica).';
COMMENT ON COLUMN raw.job_observations.raw_payload IS 'Payload bruto do scraper (JSONB), sem normalização de negócio.';
COMMENT ON COLUMN raw.job_observations.is_relevant IS 'True se a vaga passou no filtro de relevância (título).';
