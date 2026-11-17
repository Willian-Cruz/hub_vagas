-- 007: tabela de controle de migrações aplicadas (schema_migrations).
--
-- Registra cada arquivo de migração SQL já executado no banco, para que o
-- script infra/migrate.py aplique apenas o que ainda falta. É idempotente.
--
-- Estrutura:
--   arquivo       - nome do arquivo de migração (ex: 006_raw_job_observations.sql)
--   aplicado_em   - timestamp de quando foi aplicada
--   checksum_sha256 - hash do conteudo do arquivo (para detectar alteracoes)

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    arquivo            TEXT           PRIMARY KEY,
    aplicado_em        TIMESTAMPTZ    NOT NULL DEFAULT now(),
    checksum_sha256    TEXT           NOT NULL
);

COMMENT ON TABLE public.schema_migrations IS
    'Controle de versao do schema: quais arquivos de migracao ja foram aplicados.';
COMMENT ON COLUMN public.schema_migrations.arquivo IS 'Nome do arquivo SQL em infra/migrations/.';
COMMENT ON COLUMN public.schema_migrations.aplicado_em IS 'Timestamp de aplicacao.';
COMMENT ON COLUMN public.schema_migrations.checksum_sha256 IS 'SHA-256 do conteudo do arquivo (detecta alteracoes retroativas).';
