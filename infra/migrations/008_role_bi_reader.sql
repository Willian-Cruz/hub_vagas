-- 008: role somente leitura bi_reader para consumo (Power BI, metabase, etc.)
--
-- Criar a role bi_reader com login e senha definida FORA do repositório.
-- A role tem CONNECT no banco e USAGE + SELECT apenas nos schemas gold e bronze.
-- Os schemas podem não existir ainda (são criados pelo dbt), portanto usamos
-- CREATE SCHEMA IF NOT EXISTS e DO $$ para evitar falha em banco limpo.

-- Executar como o usuário que o dbt usa (dono do schema gold).
-- Defina a senha fora do repositório (nunca commitá-la).

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bi_reader') THEN
        CREATE ROLE bi_reader LOGIN PASSWORD '<defina-fora-do-repo>';
    END IF;
END
$$;

CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS bronze;

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.schemata WHERE schema_name = 'gold') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA gold TO bi_reader';
        EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA gold TO bi_reader';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO bi_reader';
    END IF;
    IF EXISTS (SELECT FROM information_schema.schemata WHERE schema_name = 'bronze') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA bronze TO bi_reader';
        EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA bronze TO bi_reader';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT SELECT ON TABLES TO bi_reader';
    END IF;
END
$$;
