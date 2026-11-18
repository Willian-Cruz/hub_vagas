-- 010: adiciona coluna fisica `link` em raw.job_observations
--
-- A coluna `link` (URL da vaga) era armazenada apenas dentro de raw_payload (JSONB).
-- Para suportar consultas diretas, identidade da vaga e deduplicacao na camada Raw,
-- ela agora e uma coluna física da tabela.
--
-- Esta migration e idempotente: ADD COLUMN IF NOT EXISTS nao duplica a coluna.

ALTER TABLE raw.job_observations
    ADD COLUMN IF NOT EXISTS link TEXT;

CREATE INDEX IF NOT EXISTS ix_job_observations_link
    ON raw.job_observations (link);

COMMENT ON COLUMN raw.job_observations.link IS 'URL canônica da vaga, extraída do raw_payload. Usada para identidade, deduplicação e rastreabilidade.';
