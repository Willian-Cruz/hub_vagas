-- 008: role somente leitura bi_reader para consumo (Power BI, metabase, etc.)
--
-- Criar a role bi_reader com login e senha definida FORA do repositório.
-- A role tem CONNECT no banco e USAGE + SELECT apenas no schema gold.
-- O dbt recria as tabelas a cada build e perde os grants, por isso
-- dbt_project.yml declara +grants: select: ['bi_reader'] para os modelos gold.

-- Executar como o usuário que o dbt usa (dono do schema gold).
-- Defina a senha fora do repositório (nunca commitá-la).

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bi_reader') THEN
        CREATE ROLE bi_reader LOGIN PASSWORD '<defina-fora-do-repo>';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA gold TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO bi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO bi_reader;

-- Opcional: tambem concede SELECT em bronze.scrape_runs para monitoramento de
-- fontes (nao é obrigatorio, apenas leitura).
GRANT USAGE ON SCHEMA bronze TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA bronze TO bi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT SELECT ON TABLES TO bi_reader;
