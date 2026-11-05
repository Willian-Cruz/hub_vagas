# Hub Vagas — Job Market Analytics

[![CI Hub Vagas](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml/badge.svg)](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy-336791?logo=postgresql&logoColor=white)
![Playwright](https://img.shields.io/badge/Coleta-Playwright-2EAD33?logo=playwright&logoColor=white)
![Power BI](https://img.shields.io/badge/Dashboard-Power%20BI-F2C811?logo=powerbi&logoColor=black)
![License](https://img.shields.io/badge/licen%C3%A7a-MIT-lightgrey)

Pipeline de dados que coleta vagas de Dados e Tecnologia em portais brasileiros. Python captura os registros na camada Bronze; dbt padroniza e deduplica na Silver e publica agregações na Gold. A tabela `jobs` continua sendo mantida durante a transição para preservar os consumidores atuais de Excel e Power BI.

A execução é em **lote (batch)**: uma vez por dia via APScheduler, ou manualmente.

---

## Arquitetura

```mermaid
flowchart LR
    A[Portais de vagas<br/>Vagas.com · InfoJobs · Gupy] --> B[Scrapers<br/>Playwright + BeautifulSoup]
    B --> C[(Bronze<br/>PostgreSQL JSONB)]
    C --> D[dbt staging e Silver<br/>limpeza · padronização · deduplicação]
    D --> E[dbt Gold<br/>marts analíticos]
    C --> L[(jobs legado<br/>compatibilidade durante a transição)]
    L --> F[Exportação atual<br/>Excel .xlsx]
    F --> G[Dashboard<br/>Power BI]
```

| Etapa | Onde fica | O que faz |
| --- | --- | --- |
| Coleta | `app/scrapers/`, `app/services/collector_service.py`, `app/services/relevance_service.py` | Roda cada scraper em sequência, descarta vagas cujo **título** não é da área de dados (a contagem vai para o log e as métricas) e preserva fragmentos HTML dos cards capturados |
| Bronze | `app/database/bronze_model.py`, `app/repositories/bronze_repository.py` | Registra snapshots append-only em JSONB, hash, `run_id`, data e resultado por fonte |
| Silver | `dbt/models/staging/`, `dbt/models/intermediate/jobs.sql` | Campo sem informação é `NULL`, nunca "Não informado". Padroniza senioridade (infere do título se o portal não informa), localidade e modalidade; identifica salário divulgado; mantém a observação mais recente por ID no portal e junta a mesma vaga republicada com outro ID (título + empresa + local) |
| Gold | `dbt/models/marts/` | Publica exportação pronta de vagas, volume diário, snapshot por localidade/fonte, demanda de tecnologias e status dos scrapers |
| Compatibilidade | `app/repositories/job_repository.py` | Mantém a tabela `jobs` atual durante a migração. Duplicada = mesmo link, ou mesmo ID no portal (`origem` + `id_externo`), ou mesmo conteúdo; ao reencontrar a vaga só preenche campos `NULL` |
| Orquestração e exportação | `app/services/pipeline_service.py`, `app/main.py`, `app/scheduler.py`, `app/services/export_service.py` | Registra métricas, roda dbt no comando manual ou com `--com-dbt` no agendador e exporta o mart Gold para Excel/Power BI |

## Modelo de dados

```mermaid
erDiagram
    scrape_runs ||--o{ job_observations : registra
    scrape_runs {
        uuid run_id PK
        string source PK
        string status
        int jobs_found
        datetime started_at
        datetime finished_at
    }
    job_observations {
        bigint id PK
        uuid run_id FK
        string source FK
        string source_job_id
        datetime collected_at
        string payload_hash
        jsonb raw_payload
    }
    jobs ||--o{ job_technologies : possui
    technologies ||--o{ job_technologies : aparece_em
    jobs {
        int id PK
        string titulo
        string empresa
        string senioridade
        string localizacao
        text descricao
        string salario
        string link UK
        string origem
        string id_externo "UK com origem"
        datetime data_publicacao
        string modalidade
        string experiencia
        string escolaridade
        int qtd_posicoes
        string chave_conteudo
        datetime data_coleta
    }
    technologies {
        int id PK
        string nome UK
    }
    job_technologies {
        int job_id FK
        int technology_id FK
    }
```

---

## Estrutura do projeto

```text
hub_vagas/
├── .github/workflows/
│   └── tests.yml              # CI: roda a suíte de testes a cada push e PR na main
├── app/
│   ├── config/settings.py     # leitura do .env
│   ├── constants/selectors.py # seletores CSS dos portais
│   ├── database/              # conexão e modelos SQLAlchemy (Bronze e tabelas legadas)
│   ├── repositories/          # persistência Bronze e repositórios legados
│   ├── schemas/job_schema.py  # validação Pydantic
│   ├── scrapers/              # base_scraper, vagas_scraper, infojobs_scraper, gupy_scraper
│   ├── services/              # analytics, collector, export, job, normalize, pipeline,
│   │                          # relevance, salary, scheduler, tech
│   ├── tests/                 # testes + conftest.py (banco mockado) + fixtures/ (HTML real dos portais)
│   ├── utils/                 # logger (rotação de arquivo), text_utils, date_utils
│   ├── debug_vagas.py         # diagnóstico visual do scraper do Vagas.com
│   ├── export_excel.py        # ponto de entrada da exportação
│   ├── main.py                # execução única do pipeline
│   ├── run_dbt.py             # CLI dbt com credenciais carregadas do .env
│   └── scheduler.py           # execução agendada
├── dbt/                       # projeto dbt: sources, staging, Silver, Gold e testes
├── infra/migrations/          # SQL para bancos criados por versões anteriores (001 a 004)
├── .env.example
├── requirements.txt
└── LICENSE
```

---

## Portais

| Portal | Situação |
| --- | --- |
| Vagas.com | Implementado: ID, data de publicação, posições, local, nível e descrição do card |
| InfoJobs | Implementado: salário, experiência, escolaridade, modalidade, data exata e ID |
| Gupy | Implementado, com calibração de seletores pendente (`app/scrapers/gupy_scraper.py`) |
| Catho, Remotar, Sólides | Próximos (mesmo contrato dos scrapers atuais) |
| LinkedIn, Indeed, Glassdoor | Planejados |

## Tecnologias identificadas nas descrições

18 termos monitorados em `app/services/tech_service.py`: Python, SQL, AWS, Azure, GCP, Spark, Airflow, Kafka, Docker, Kubernetes, PostgreSQL, MySQL, Oracle, MongoDB, Power BI, Tableau, Databricks e Snowflake.

---

## Como executar

### 1. Instalação

```bash
git clone https://github.com/Willian-Cruz/hub_vagas.git
cd hub_vagas
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configuração

```bash
cp .env.example .env
```

```env
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hub_vagas
```

Se o InfoJobs não conseguir validar o certificado TLS em uma rede com proxy
corporativo, configure `REQUESTS_CA_BUNDLE` com o caminho do certificado CA
fornecido pela rede. A validação TLS continua habilitada.

Na configuração local (`DB_*`), `main.py` cria o banco se ele ainda não existir
e depois cria as tabelas. O usuário PostgreSQL configurado precisa ter o
privilégio `CREATEDB`. Em uma conexão remota via `DATABASE_URL`, crie o banco
no provedor antes de executar o pipeline.

`create_all()` não altera tabelas já existentes. Para bancos criados por versões
anteriores, aplique as migrações de `infra/migrations` em ordem. A migração `001`
adiciona a chave da tabela de associação e interrompe se encontrar pares
duplicados. A migração `002` adiciona `jobs.data_coleta`; vagas antigas recebem
como data de coleta o momento da migração, pois a versão anterior não guardava
esse timestamp. A migração `003` cria as tabelas Bronze (`main.py` e
`scheduler.py` também as criam automaticamente).

A migração `004` (idempotente) adiciona em `jobs` os campos `id_externo`,
`data_publicacao`, `modalidade`, `experiencia`, `escolaridade`, `qtd_posicoes` e
`chave_conteudo`; preenche `id_externo` a partir dos links já gravados; troca os
textos "Não informado", "Confidencial" e "Localização Não Informada" por `NULL`;
e cria o índice único `(origem, id_externo)`. Ela **interrompe** se houver ID
repetido no mesmo portal. Faça um backup antes de aplicar:

```bash
# use os valores de DB_USER, DB_NAME, DB_HOST e DB_PORT do seu .env
# (no PowerShell, prefira -f a ">": o redirecionamento grava em UTF-16)
pg_dump -h localhost -p 5432 -U usuario -d hub_vagas -f backup_antes_da_004.sql
psql -h localhost -p 5432 -U usuario -d hub_vagas -f infra/migrations/004_jobs_novos_campos.sql
```

Com uma `DATABASE_URL` completa (banco remoto), passe a URL entre aspas no lugar
dos parâmetros: `pg_dump "postgresql://usuario:senha@host:5432/banco" -f backup.sql`.

Campo sem informação é `NULL`, nunca o texto "Não informado". No Power BI, trate
`NULL` como "(Em branco)". A `data_coleta` de vagas anteriores à migração `002` não
é confiável (todas recebem o horário da migração); use `data_publicacao`.

### 3. Pipeline

```bash
# Execução única: coleta, Bronze, compatibilidade `jobs` e dbt build.
# Sai com código 1 se a coleta/persistência ou os modelos/testes dbt falharem.
python app/main.py

# Executar somente transformações dbt ou verificar conexão/freshness
python app/run_dbt.py debug
python app/run_dbt.py source freshness
python app/run_dbt.py build

# Execução agendada: todo dia às 06:00, horário de São Paulo (padrão)
python app/scheduler.py --com-dbt
python app/scheduler.py --hora 8 --minuto 30 --com-dbt  # horário customizado
python app/scheduler.py --intervalo 2 --com-dbt         # a cada N horas (debug)
```

Exemplo de log:

```text
PIPELINE INICIADO
Etapa 1/3: Coletando vagas...
Coletadas: 87 vagas | Descartadas (fora do tema): 214
Etapa 2/3: Gravando observações na camada Bronze...
Bronze concluída — 87 observação(ões)
Etapa 3/3: Atualizando a tabela legada jobs...
Persistência concluída — Salvas: 54 | Duplicadas: 33 | Erros: 0
PIPELINE CONCLUÍDO
Executando modelos e testes dbt...
```

O payload Bronze guarda os campos retornados pelo contrato do scraper e o HTML
do card capturado, sem normalização de negócio. `run_id` identifica a execução;
`payload_hash` permite comparar alterações entre coletas. A tabela
`bronze.scrape_runs` também registra fontes vazias ou com falha, permitindo
acompanhar a última execução e verificar freshness mesmo quando não há vagas.

O comando `app/run_dbt.py` lê `.env` e configura a conexão dbt a partir de
`DATABASE_URL` ou das variáveis `DB_*`. O dbt cria os schemas `silver` e `gold`
durante o `build`; o usuário do PostgreSQL precisa ter permissão para criar
schemas e tabelas. O perfil sem segredos é copiado de
`dbt/profiles.yml.example` para o arquivo local ignorado `dbt/profiles.yml`.
As fontes são declaradas em `dbt/models/sources.yml`.

Os logs ficam em `logs/pipeline.log`, com rotação a cada 5 MB (3 backups).

### 4. Exportação para Excel / Power BI

```bash
cd app
python export_excel.py
```

Gera `data/exports/vagas.xlsx` a partir de `gold.mart_vagas` (inclui `id_externo`,
`data_publicacao`, `modalidade`, `experiencia`, `escolaridade` e `qtd_posicoes`;
datas no horário de São Paulo), que alimenta o dashboard no Power BI. Execute `python app/main.py` ou `python app/run_dbt.py build`
antes de exportar.

---

## Testes

```bash
cd app
pytest tests/ -v
```

A suíte usa um mock global do banco (`conftest.py`), então roda sem PostgreSQL. Os testes cobrem scrapers, normalização, salário, analytics, repositórios (inclusive deduplicação por ID e conteúdo e a gravação Bronze), relevância, pipeline, agendamento, exportação, `run_dbt` e configuração. Os parsers do Vagas.com e do InfoJobs também são testados contra **HTML real** dos portais (`app/tests/fixtures/`); quando um portal mudar o layout, salve os cards novos ali e ajuste `test_parsers_html_real.py`. Instale as dependências com `pip install -r requirements.txt` antes de executá-los. O GitHub Actions roda a suíte a cada push e pull request na `main`.

Os testes de dados dbt são executados por `python app/run_dbt.py build` junto
com os modelos; os de `dbt/tests/` protegem o contrato de `NULL` e a deduplicação
da Silver (ID no portal e conteúdo). Para verificar a atualização das fontes, execute
`python app/run_dbt.py source freshness` após pelo menos uma coleta.

---

## Histórico

| Etapa | Entregas |
| --- | --- |
| 1 a 2 | Estrutura, conexão com PostgreSQL, persistência e validação com Pydantic |
| 3 | Scrapers do Vagas.com e InfoJobs, coleta consolidada no CollectorService |
| 4 | Extração de tecnologias e relação many-to-many `jobs` ↔ `technologies` |
| 5 | Normalização de senioridade e localização, extração de salário |
| 6 a 7 | AnalyticsService, PipelineService com métricas, APScheduler e logging estruturado |
| 8 | Deploy em Render (Cron Job + PostgreSQL), Docker e dashboard HTML no GitHub Pages |
| 9 (jun/2026) | Deploy em nuvem e dashboard HTML descontinuados; análise migrada para exportação Excel + Power BI |
| 10 (out/2026) | Correções de métricas do pipeline, código de saída do `main.py` e testes do repositório |
| 11 (nov/2026) | Revisão dos scrapers do Vagas.com e InfoJobs com HTML real: campos vazios viram `NULL`, novos campos, filtro de relevância, deduplicação por ID e conteúdo, migração `004`; Silver/Gold passam a levar os campos novos, `NULL` e deduplicação; correções na gravação Bronze, no `run_dbt.py` e na exportação para Excel |

---

## Próximos passos

- Calibrar os seletores do scraper da Gupy
- Publicar prints do dashboard do Power BI neste README
- Adicionar Catho, Remotar e Sólides, e depois LinkedIn, Indeed e Glassdoor
- Buscar a página de detalhe da vaga (descrição completa e salário) nos portais que só mostram um resumo no card

---

## Autor

**Willian da Cruz** — projeto de estudo e portfólio em Engenharia de Dados.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-williandacruz-0A66C2?logo=linkedin)](https://www.linkedin.com/in/williandacruz/)
[![GitHub](https://img.shields.io/badge/GitHub-Willian--Cruz-181717?logo=github)](https://github.com/Willian-Cruz)

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).

