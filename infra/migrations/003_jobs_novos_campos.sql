-- 003: novos campos de coleta, limpeza de placeholders e chave de deduplicação.
--
-- Rode UMA vez no banco hub_vagas, depois de um backup (pg_dump). É idempotente:
-- rodar de novo não altera nada que já foi ajustado.
--
-- O que faz:
--   1. adiciona as colunas que o card do portal já traz (id_externo, data_publicacao,
--      modalidade, experiencia, escolaridade, qtd_posicoes) e a chave_conteudo;
--   2. preenche id_externo das vagas antigas a partir do link;
--   3. troca por NULL os textos que eram placeholder ("Não informado",
--      "Localização Não Informada", empresa "Confidencial");
--   4. corrige a capitalização de cidades ("Rio De Janeiro" -> "Rio de Janeiro");
--   5. cria o índice único (origem, id_externo), parando antes se houver repetidos.

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS id_externo      VARCHAR,
    ADD COLUMN IF NOT EXISTS data_publicacao TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS modalidade      VARCHAR,
    ADD COLUMN IF NOT EXISTS experiencia     VARCHAR,
    ADD COLUMN IF NOT EXISTS escolaridade    VARCHAR,
    ADD COLUMN IF NOT EXISTS qtd_posicoes    INTEGER,
    ADD COLUMN IF NOT EXISTS chave_conteudo  VARCHAR;

CREATE INDEX IF NOT EXISTS ix_jobs_chave_conteudo ON jobs (chave_conteudo);

-- 2) ID da vaga no portal, extraído do link já gravado
UPDATE jobs SET id_externo = substring(link FROM '/vagas/v([0-9]+)')
 WHERE id_externo IS NULL AND origem = 'Vagas.com';

UPDATE jobs SET id_externo = substring(link FROM '__([0-9]+)\.aspx')
 WHERE id_externo IS NULL AND origem = 'InfoJobs';

UPDATE jobs SET id_externo = substring(link FROM '/jobs/([0-9]+)')
 WHERE id_externo IS NULL AND origem = 'Gupy';

-- 3) Placeholders viram NULL
UPDATE jobs SET empresa = NULL
 WHERE btrim(empresa) IN ('', 'Não informado', 'Nao informado', 'Confidencial');

UPDATE jobs SET senioridade = NULL
 WHERE btrim(senioridade) IN ('', 'Não informado', 'Nao informado');

UPDATE jobs SET localizacao = NULL
 WHERE btrim(localizacao) IN ('', 'Não informado', 'Nao informado',
                              'Localização Não Informada', 'Localização não informada');

UPDATE jobs SET descricao = NULL
 WHERE btrim(descricao) IN ('', 'Não informado', 'Nao informado');

UPDATE jobs SET salario = NULL
 WHERE btrim(salario) IN ('', 'Não informado', 'Nao informado');

-- 4) Preposições em minúsculas nos nomes de cidade
UPDATE jobs
   SET localizacao = replace(replace(replace(replace(replace(localizacao,
           ' De ', ' de '), ' Da ', ' da '), ' Do ', ' do '), ' Das ', ' das '), ' Dos ', ' dos ')
 WHERE localizacao ~ ' (De|Da|Do|Das|Dos) ';

-- 5) Índice único (origem, id_externo). Para se já houver repetidos.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM jobs
        WHERE id_externo IS NOT NULL
        GROUP BY origem, id_externo
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'jobs tem (origem, id_externo) repetidos; revise e remova os duplicados antes de aplicar o indice unico';
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_origem_id_externo ON jobs (origem, id_externo);

-- Conferência opcional depois de rodar: vagas repetidas por conteúdo (mesmo título,
-- empresa e local, IDs diferentes). A chave_conteudo das vagas antigas é preenchida
-- pelo pipeline quando a vaga aparece de novo numa coleta; até lá, use esta consulta:
--
--   SELECT origem, lower(titulo) AS titulo, empresa, localizacao,
--          COUNT(*) AS n, array_agg(id ORDER BY id) AS ids
--   FROM jobs
--   WHERE empresa IS NOT NULL AND localizacao IS NOT NULL
--   GROUP BY 1, 2, 3, 4
--   HAVING COUNT(*) > 1;
