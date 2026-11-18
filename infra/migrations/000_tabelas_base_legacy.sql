-- 000: cria tabelas base legacy (public.jobs, public.technologies, public.job_technologies)
--
-- As migrations subsequentes (001+) pressupoem que essas tabelas ja existem.
-- Esta migration e idempotente e deve ser aplicada primeiro em bancos limpos.

CREATE TABLE IF NOT EXISTS jobs (
    id                SERIAL      PRIMARY KEY,
    titulo            VARCHAR(255) NOT NULL,
    empresa           VARCHAR(255),
    senioridade       VARCHAR(100),
    localizacao       VARCHAR(255),
    descricao         TEXT,
    salario           VARCHAR(100),
    link              VARCHAR(2048) UNIQUE NOT NULL,
    origem            VARCHAR(100),
    data_coleta       TIMESTAMP WITHOUT TIME ZONE,
    id_externo        VARCHAR(100),
    data_publicacao   TIMESTAMP WITHOUT TIME ZONE,
    modalidade        VARCHAR(50),
    experiencia       VARCHAR(100),
    escolaridade      VARCHAR(100),
    qtd_posicoes      INTEGER,
    chave_conteudo    VARCHAR(500),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS technologies (
    id    SERIAL      PRIMARY KEY,
    nome  VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS job_technologies (
    job_id         INTEGER NOT NULL,
    technology_id  INTEGER NOT NULL,
    PRIMARY KEY (job_id, technology_id),
    FOREIGN KEY (job_id)      REFERENCES jobs(id),
    FOREIGN KEY (technology_id) REFERENCES technologies(id)
);

CREATE INDEX IF NOT EXISTS ix_jobs_origem ON jobs (origem);
CREATE INDEX IF NOT EXISTS ix_jobs_link ON jobs (link);

COMMENT ON TABLE jobs IS 'Tabela legacy pública de vagas. Mantida por compatibilidade; nao e mais gravada pelo Python.';
COMMENT ON TABLE technologies IS 'Catalogo de tecnologias (legado).';
COMMENT ON TABLE job_technologies IS 'Associacao many-to-many entre vagas e tecnologias (legado).';
