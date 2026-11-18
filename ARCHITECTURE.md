# Hub Vagas — Documentação Arquitetural

> **Versão:** 1.0 | **Data:** 2026-11-17 | **Status:** Em desenvolvimento (execução local)

---

## 1. Visão Geral da Arquitetura

```mermaid
flowchart LR
    A[PORTALS<br/>Vagas.com · InfoJobs · Gupy · Catho] --> B[INGESTÃO<br/>Python/Playwright/requests<br/>app/main.py · app/scheduler.py]
    B --> C[(RAW<br/>raw.job_observations<br/>payload bruto JSONB + is_relevant])
    C --> D[SILVER<br/>silver.jobs<br/>normalização + dedup]
    D --> E[GOLD<br/>gold.mart_*<br/>analytics]
    E --> F[EXPORT<br/>Excel .xlsx]
    F --> G[BI<br/>Power BI]
    B -.-> H[BRONZE<br/>bronze.scrape_runs<br/>metadado de execução<br/>não é camada de dados]
    H -->|alimenta| I[mart_status_fontes]
```

**Princípio fundamental:** Separação de responsabilidades
- **Python (`app/`)**: Apenas ingestão (scrape → Raw `public.jobs` + Bronze `scrape_runs`)
- **dbt (`dbt/`)**: Todas as transformações (Raw → Bronze → Silver → Gold)

---

## 2. Estrutura de Diretórios

```
hub_vagas/
├── app/                          # Camada de aplicação (Python)
│   ├── database/                 # ORM SQLAlchemy + conexão
│   │   ├── connection.py         # Engine, sessão, criação DB
│   │   ├── models.py             # Base declarativa
│   │   ├── job_model.py          # Tabela raw jobs (legado, migração 004)
│   │   ├── bronze_model.py       # Tabela bronze.scrape_runs
│   │   ├── repositories/         # Data Access Layer
│   │   │   ├── job_repository.py # Persistência append-only em raw.job_observations
│   │   │   └── bronze_repository.py  # Persistência scrape_runs
│   │   ├── scrapers/             # Coletores por portal
│   │   │   ├── base_scraper.py   # Template Method + retry + rate-limit + compliance
│   │   │   ├── vagas_scraper.py  # Playwright + BeautifulSoup
│   │   │   ├── infojobs_scraper.py   # requests + BeautifulSoup
│   │   │   ├── gupy_scraper.py       # Playwright (seletores a calibrar)
│   │   │   ├── catho_scraper.py      # requests + parser dedicado
│   │   │   ├── catho_parser.py       # Parser HTML Catho
│   │   │   └── parser_utils.py       # Utilitários de parsing
│   │   ├── schemas/                  # Validação Pydantic
│   │   │   └── job_schema.py         # JobSchema (contrato de entrada)
│   │   ├── services/                 # Regras de negócio
│   │   │   ├── collector_service.py  # Orquestra scrapers + filtro de relevância
│   │   │   ├── pipeline_service.py   # Pipeline ingestão completa (advisory lock + notifier)
│   │   │   ├── relevance_service.py  # Filtro por título (termos de dados)
│   │   │   ├── normalize_service.py  # Normalização: local, empresa, modalidade
│   │   │   ├── export_service.py     # Geração Excel
│   │   │   └── scheduler_service.py  # APScheduler (cron/intervalo)
│   │   ├── utils/                    # Utilitários
│   │   │   ├── logger.py             # Logging rotativo (5MB, 3 backups)
│   │   │   ├── text_utils.py         # Normalização texto, chave_conteudo
│   │   │   └── date_utils.py         # Parsing datas relativas/absolutas
│   │   ├── tests/                    # Testes unitários + integração
│   │   │   ├── conftest.py           # Mock global DB (SQLAlchemy)
│   │   │   ├── fixtures/             # HTML real dos portais
│   │   │   └── test_*.py             # Testes passando (suíte mockada, sem PostgreSQL)
│   │   ├── main.py                   # Entrypoint: scrape → raw.job_observations
│   │   ├── transform.py              # Entrypoint: dbt build
│   │   ├── run_dbt.py                # Wrapper dbt (carrega .env → profiles.yml)
│   │   ├── scheduler.py              # Agendador CLI (diário/intervalo)
│   │   ├── notifier.py               # Webhook/e-mail de falha
│   │   └── export_excel.py           # Exporta gold.mart_vagas → .xlsx
│
├── dbt/                          # Camada de transformação (SQL)
│   ├── macros/                   # Macros reutilizáveis
│   │   ├── select_raw_jobs.sql   # Seleciona raw por fonte
│   │   │   normalize_*.sql       # Normalização campos (senioridade, salário, localização)
│   │   │   ├── classify_seniority_cascade.sql  # Senioridade SQL
│   │   │   ├── monitored_technologies.sql      # Techs monitoradas (regex sobre seed)
│   │   │   └── generate_schema_name.sql        # Nomes de schema dinâmicos
│   │   ├── models/
│   │   │   ├── sources.yml           # Fontes: raw_observations.job_observations + bronze.scrape_runs
│   │   │   ├── staging/              # Views por fonte (stg_*_jobs), lê de raw_observations.job_observations
│   │   │   ├── intermediate/         # Silver: int_jobs_unioned → int_jobs_normalized → int_jobs_deduped → silver.jobs
│   │   │   │   └── intermediate.yml  # Testes Silver
│   │   │   └── marts/                # Gold: mart_vagas, mart_vagas_por_dia, etc. (+grants bi_reader)
│   │   │       └── marts.yml         # Testes Gold
│   │   ├── seeds/                    # tecnologias_monitoradas.csv, termos_relevancia.csv (fonte única)
│   │   ├── tests/                    # Testes de qualidade de dados
│   │   │   ├── assert_silver_*.sql   # Unicidade, NULL%, freshness, placeholders, contrato Python↔dbt
│   │   │   └── assert_gold_tecnologias.sql
│   │   ├── dbt_project.yml           # Config dbt (vars: freshness, qualidade, volume; +grants bi_reader)
│   │   └── profiles.yml.example      # Template perfis (sem segredos)
│
├── docs/
│   ├── adr/
│   │   ├── 0001-jobs-como-raw.md
│   │   └── 0002-filtro-de-relevancia.md
│   └── compliance.md               # Conformidade da coleta (robots.txt, termos, rate limit)
│
├── infra/migrations/             # Evolução schema (001-008)
├── scripts/                      # Utilitários operacionais
│   ├── task_hub_vagas_coletadiaria.xml   # Agendador de Tarefas Windows
│   └── registrar_tarefa_coletadiaria.ps1 # Registra a tarefa no Windows
├── .env.example                  # Template variáveis ambiente
├── requirements.in               # Dependências não-pinadas (fonte para pip-compile)
├── requirements.txt              # Dependências travadas (saída do pip-compile)
└── README.md                     # Documentação completa (histórico; fonte da verdade: ARCHITECTURE.md)
```

---

## 3. Fluxo de Dados Detalhado

### 3.1 Ingestão (Python) — `app/main.py` → `PipelineService`

```mermaid
flowchart TD
    A[CollectorService.coletar_resultados] --> B[Para cada scraper]
    B --> C[scraper.coletar → ScrapeResult]
    C --> D[RelevanceService.separar]
    D --> E[PipelineService.executar]
E --> F[JobRepository.salvar → raw.job_observations]
E --> G[BronzeRepository.persistir_resultados → bronze.scrape_runs]
```

**Detalhes do `JobRepository.salvar()`:**
1. Grava o payload bruto em `raw.job_observations` (append-only), sem normalização de negócio (senioridade, local, salário, modalidade, tecnologias ficam para o dbt).
2. Busca duplicata por `(origem, id_externo)` + `payload_hash`: se a última observação da mesma vaga no portal tiver o mesmo payload, não insere novamente e retorna `"duplicada"`.
3. Se nova: INSERT em `raw.job_observations` com `raw_payload`, `payload_hash`, `is_relevant` e retorna `"salva"`.
4. Erro de persistência: rollback e retorna `"erro"`.

### 3.2 Transformação (dbt) — `dbt build`

```mermaid
flowchart TD
    subgraph STAGING [STAGING - Views]
        S1[stg_vagas_com_jobs]
        S2[stg_infojobs_jobs]
        S3[stg_gupy_jobs]
        S4[stg_catho_jobs]
    end

    subgraph SILVER [INTERMEDIATE / SILVER - Table: silver.jobs]
        I1[source_rows = UNION ALL 4 staging]
        I2[cleaned = NULL se placeholder]
        I3[normalized = senioridade cascade + local + salário]
        I4[keyed = modalidade + chave_portal + chave_conteudo]
        I5[latest_per_portal_id = ROW_NUMBER PARTITION BY origem,chave_portal]
        I6[ranked = ROW_NUMBER PARTITION BY chave_conteudo]
        I7[SELECT WHERE content_rank = 1]
    end

    subgraph GOLD [MARTS / GOLD - Tables]
        G1[mart_vagas = silver.jobs + tecnologias]
        G2[mart_vagas_por_dia = silver.jobs GROUP BY data,origem]
        G3[mart_vagas_por_origem_localidade = silver.jobs GROUP BY orig,loc,sen]
        G4[mart_demanda_tecnologias = CROSS JOIN techs + regex desc]
        G5[mart_status_fontes = bronze.scrape_runs latest/run]
    end

    S1 & S2 & S3 & S4 --> I1
    I1 --> I2 --> I3 --> I4 --> I5 --> I6 --> I7
    I7 --> G1 & G2 & G3 & G4
    S1 & S2 & S3 & S4 --> G5
```

---

## 4. Modelos de Dados por Camada

### 4.1 Raw — `raw.job_observations` (Landing Zone, append-only)

| Coluna | Tipo | Constraints | Origem |
|--------|------|-------------|--------|
| `id` | bigserial | PK | Auto |
| `run_id` | uuid | NOT NULL | Pipeline (UUID da execução) |
| `source` | text | NOT NULL | Scraper (Vagas.com, InfoJobs, Gupy, Catho) |
| `source_job_id` | text | | Scraper (id_externo, pode ser NULL) |
| `collected_at` | timestamptz | NOT NULL | Pipeline |
| `payload_hash` | text | NOT NULL | Repository (SHA-256 do raw_payload) |
| `raw_payload` | jsonb | NOT NULL | Scraper (payload bruto, sem normalização) |
| `is_relevant` | boolean | NOT NULL DEFAULT true | RelevanceService (filtro por título) |
| `created_at` | timestamptz | NOT NULL DEFAULT now() | Pipeline |

**Dedup Raw**: mesma `(source, source_job_id)` + `payload_hash` não é regravada (última observação vence).

A tabela pública `public.jobs` é mantida como legado (migração `004`); não é mais gravada pelo Python. O dbt lê de `raw.job_observations` através da fonte `raw_observations.job_observations`.

### 4.2 Bronze — `bronze.scrape_runs` (Monitoramento)

| Coluna | Tipo | Constraints |
|--------|------|-------------|
| `run_id` | uuid | PK (com source) |
| `source` | string | PK (com run_id) |
| `status` | string | success\|empty\|partial\|failed |
| `pages_processed` | int | DEFAULT 0 |
| `jobs_found` | int | DEFAULT 0 |
| `error` | text | |
| `started_at` | timestamptz | NOT NULL |
| `finished_at` | timestamptz | NOT NULL |
| `created_at` | timestamptz | DEFAULT now() |

### 4.3 Silver — `silver.jobs` (Normalizada + Dedup)

| Coluna | Tipo | Notas |
|--------|------|-------|
| `raw_job_id` | int | FK para raw.id |
| `origem` | string | |
| `link` | string | |
| `id_externo` | string | |
| `titulo` | string | NOT NULL |
| `empresa` | string | NULL = desconhecido |
| `senioridade` | string | Normalizada (9 valores) |
| `localizacao` | string | Preposições minúsculas |
| `descricao` | text | |
| `salario_texto` | string | Salário como publicado (ex: "R$ 3.000,00") |
| `salario_min` | numeric | Valor mínimo extraído |
| `salario_max` | numeric | Valor máximo extraído |
| `salario_tipo` | string | faixa/exato/a_combinar/nao_informado |
| `modalidade` | string | Remoto/Híbrido/Presencial/NULL |
| `experiencia` | string | |
| `escolaridade` | string | |
| `qtd_posicoes` | int | |
| `data_publicacao` | timestamptz | UTC; precisão em `data_publicacao_precisao` |
| `data_atualizacao` | timestamptz | UTC; apenas Catho preenche |
| `chave_conteudo` | string | Dedup cross-portal |
| `data_coleta` | timestamptz | |
| `dedup_group_id` | string | Grupo de dedup |
| `first_seen_at` | timestamptz | Primeira coleta do grupo |
| `last_seen_at` | timestamptz | Última coleta do grupo |
| `is_canonical` | boolean | true = linha mais recente do grupo |
| `dias_no_ar` | numeric | Diferença entre first_seen_at e last_seen_at em dias |
| `is_ativa` | boolean | true se vista nos últimos 3 dias |

**Dedup Silver:** todas as linhas são mantidas (nenhuma apagada); cada grupo de conteúdo recebe `dedup_group_id`, `first_seen_at`/`last_seen_at` e `is_canonical` (linha mais recente do grupo). Os marts usam apenas `is_canonical = true`. A dedup é por portal: a mesma vaga em dois portais conta duas vezes.

### 4.4 Gold — Marts Analíticos

| Mart | Granularidade | Uso |
|------|---------------|-----|
| `mart_vagas` | 1 linha/vaga (canônicas) | Export Excel, Power BI |
| `mart_vagas_por_dia` | (data, origem) | Tendência volume |
| `mart_vagas_por_origem_localidade` | (origem, local, senioridade) | Heatmap geo/sênior |
| `mart_demanda_tecnologias` | tecnologia | Ranking techs |
| `mart_status_fontes` | origem | Monitoramento freshness |
| `mart_salarios` | (origem, senioridade) | Cobertura salarial: total, n_com_salario, média, mediana |
| `mart_qualidade_campos` | (fonte, campo) | Saúde do parser por campo |

---

## 5. Padrões de Design Aplicados

| Padrão | Onde | Descrição |
|--------|------|-----------|
| **Repository Pattern** | `job_repository.py`, `bronze_repository.py` | Isola lógica de persistência; `salvar()` grava payload bruto em `raw.job_observations` sem normalização |
| **Strategy Pattern** | `base_scraper.py` + subclasses | Cada portal implementa `_buscar_pagina()` e `_parsear_cards()` |
| **Template Method** | `BaseScraper.coletar()` | Pai cuida do loop de páginas, detecção de repetida, tratamento de exceção e montagem do `ScrapeResult`; filhos implementam `_buscar_pagina()` e `_parsear_cards()` |
| **Pipeline/Chain of Responsibility** | `classify_seniority_cascade.sql` (dbt macro) | Cascata: portal → título → descrição → experiência → anos (única implementação, no dbt) |
| **Decorator (Logging)** | `utils/logger.py` | Rotação arquivo + console |
| **Factory** | `run_dbt.py` | Cria `profiles.yml` dinâmico do `.env` |
| **Configuration as Code** | `dbt_project.yml`, `dbt/seeds/*.csv`, `.env.example` | Tipagem + validação; seeds são fonte única de tecnologias e termos de relevância |
| **Idempotency** | Migrações SQL (`infra/migrate.py`), `JobRepository.salvar()` | Re-executável sem side effects; `schema_migrations` rastreia o que foi aplicado |
| **Append-Only** | `bronze.scrape_runs`, `raw.job_observations` | Histórico imutável de execuções e observações brutas |
| **Separation of Concerns** | Python (ingestão) / dbt (transformação) | Linguagem certa para cada etapa; Python não normaliza, dbt é o dono das regras de negócio |

---

## 6. Tecnologias Utilizadas

| Categoria | Tecnologia | Versão/Detalhes |
|-----------|------------|-----------------|
| **Linguagem** | Python | 3.12+ |
| **Database** | PostgreSQL | 15+ |
| **ORM** | SQLAlchemy | 2.x (sync) |
| **Validação** | Pydantic | v2 |
| **Scraping** | Playwright | Chromium (Vagas.com, Gupy) |
| **Scraping** | requests + BeautifulSoup | InfoJobs, Catho |
| **Transformação** | dbt-core + dbt-postgres | 1.9.x |
| **Agendamento** | APScheduler | Cron + intervalo |
| **Logging** | stdlib logging + rotating handler | 5MB, 3 backups |
| **Testes** | pytest | Suíte mockada (sem PostgreSQL), CI por push/PR |
| **CI/CD** | GitHub Actions | pytest a cada push/PR (`dbt build` não roda no CI: precisa de PostgreSQL) |
| **Deploy** | Histórico: Render (Cron Job + PostgreSQL) — descontinuado |
| **Export/BI** | openpyxl → Excel → Power BI | `export_service.py` |

---

## 7. Pontos de Atenção / Otimizações / Melhorias

### 7.1 Performance

| Área | Gargalo Atual | Otimização Sugerida |
|------|---------------|---------------------|
| **Scraping Vagas.com** | Playwright (browser real) lento | Avaliar API não-oficial ou request direto se possível |
| **Scraping Gupy** | Seletores não calibrados, Playwright | Priorizar calibração; considerar API GraphQL |
| **Dedup Silver** | 2 `ROW_NUMBER()` sobre 300+ rows | OK para volume atual; particionar por `data_coleta` se >100k |
| **Extração Techs** | `CROSS JOIN` 18 techs × 300 vagas = 5.4k rows | OK; usar `tsvector`/GIN index se descrições longas |
| **dbt Build** | Rebuild full a cada run | Usar modelos incrementais (`is_incremental()`) para Silver/Gold |

### 7.2 Escalabilidade

| Limitação Atual | Solução |
|-----------------|---------|
| **Single-thread scrapers** | Paralelizar `CollectorService` com `ThreadPoolExecutor` ou `asyncio` |
| **Scheduler em processo único** | Agendador de Tarefas (Windows) ou GitHub Actions schedule; Airflow/Dagster/Prefect somente se o objetivo for aprender orquestrador |
| **DB local único** | Read replicas para dbt; connection pooling (PgBouncer) |
| **Estado em memória** | Persistir `run_id` + checkpoint para resume em falha |
| **Rate limiting** | Implementar backoff exponencial + respect `robots.txt` |

### 7.3 Manutenibilidade

| Dívida Técnica | Ação |
|----------------|------|
| **Seletores CSS hardcoded** | `constants/selectors.py` OK; adicionar testes visuais de regressão |
| **Thresholds de teste hardcoded** | `assert_silver_null_pct.sql` calibrado manualmente → tornou-se configurável via `vars` em `dbt_project.yml` (P2) |
| **Cascata senioridade duplicada** | Python (`seniority_service`) + SQL (`classify_seniority_cascade`) → single source of truth (macro dbt) |
| **Gupy sem filtro relevância** | Aplicar `RelevanceService` + normalização NULL |
| **Catho sem modalidade/salario/descricao** | Buscar página de detalhe (HTML fragment já salvo no `raw_payload`) — gate robots/ToS |
| **Testes dbt SKIP em Gold** | `mart_demanda_tecnologias`, `mart_vagas`, etc. marcados como SKIP → corrigir dependências (P2) |

### 7.4 Qualidade de Dados

| Métrica | Atual | Target |
|---------|-------|--------|
| **Freshness Silver** | warn 24h / error 72h (alinhado a `sources.yml`) | < 24h (ingestão diária) |
| **NULL % modalidade** | 99.3% | < 50% (buscar página detalhe Vagas.com) |
| **NULL % salario** | 19% | < 30% (melhorar extração descrição) |
| **NULL % senioridade** | 54% | < 20% (melhorar cascata + portal) |
| **Tech detection rate** | 3.3% | > 30% (Catho sem descrição é o problema) |

**Freshness:** medir pela última coleta com `status = success` em `bronze.scrape_runs` (`finished_at`), não pela última tentativa. Limiares: `warn_after: 24h`, `error_after: 72h`, declarados em `dbt/models/sources.yml`.

**Severidade dos testes:** `severity: warn` + meta documentada para limitações conhecidas (modalidade, salário); `severity: error` para invariantes (unicidade, sem placeholder).

### 7.5 Roadmap Arquitetural (com gatilhos mensuráveis)

```
CURTO PRAZO (1-2 sprints)
├── Calibrar Gupy (seletores + relevância + NULL contract) —
│   gatilho: GUPY_ENABLED=true apenas quando houver fixtures reais
├── Buscar página detalhe Vagas.com/Catho (salário, modalidade, descrição)
│   gatilho: %NULL de salario/modalidade > 50% por 2 semanas seguidas
├── Modelos dbt incrementais (Silver/Gold) —
│   gatilho: dbt build > 5 min ou Silver > 1 milhão de linhas
└── Unificar cascata senioridade (macro dbt single source) — concluído (P3)

MÉDIO PRAZO (1-2 meses)
├── Agendamento: Agendador de Tarefas (Windows) ou GitHub Actions schedule
│   Airflow/Dagster/Prefect somente se o objetivo for aprender orquestrador
├── Adicionar portal Remotar + Sólides
├── Pipeline de alertas (webhook Discord/Telegram ou e-mail) para falhas/freshness
│   já implementado em app/notifier.py
└── Testes de contrato de schema (dbt-expectations / Great Expectations)

LONGO PRAZO (3-6 meses)
├── Data contracts formais (dbt contracts)
├── Particionamento e índices (tsvector/GIN) —
│   gatilho: Silver > 1 milhão de linhas ou consultas > 10s
└── Streaming/near-real-time —
    gatilho: necessidade de dados < 1 hora de atraso (não o caso atual com ~300 vagas)


### 7.6 Adicionar um novo portal (guia de implementação)

Todos os portais seguem o **Template Method** de `BaseScraper`. Para adicionar um
novo portal (ex.: Remotar, Sólides, LinkedIn, Indeed, Glassdoor):

1. **Criar `app/scrapers/<portal>_scraper.py`** herdando `BaseScraper`:
   - Definir `SOURCE`, `BASE_URL`, `USER_AGENT`
   - Implementar `_buscar_pagina()` (busca HTML da página de listagem)
   - Implementar `_parsear_cards()` (extrai `JobSchema` dos cards)
   - Opcional: implementar `fetch_detail_page()` para deep scraping
   - Opcional: definir `MAX_DETAIL_PAGES > 0` se deep scraping for usado

2. **Garantir o contrato de NULL**: todos os campos `Optional` devolvem `None`
   quando não há informação; nunca textos tipo "Não informado".

3. **Filtro de relevância**: aplicado centralmente em
   `CollectorService.coletar_resultados()` via `RelevanceService.separar()` —
   o scraper não precisa filtrar.

4. **Senioridade**: deixada como `None` no scraper; a normalização é feita
   exclusivamente pelo dbt (`normalize_seniority` + `classify_seniority_cascade`).

5. **Registrar em `CollectorService._SCRAPERS_BASE`** (ou usar feature flag
   `GUPY_ENABLED`-style para portais em calibração).

6. **Adicionar fonte ao `dbt/models/sources.yml`** para que o dbt staging
   leia da `raw_observations.job_observations`.

7. **Criar fixture de teste** em `app/tests/fixtures/` com HTML real do portal
   e adicionar teste em `app/tests/test_<portal>_scraper.py`.

**Ordem sugerida de expansão:** Remotar → Sólides → LinkedIn → Indeed → Glassdoor.
Cada um exige calibração de seletores contra HTML real antes de ser ativado.


Itens REMOVIDOS do roadmap (não respondem a dor real com ~300 vagas):
  ✗ Kafka + Flink (streaming desnecessário para batch diário)
  ✗ Feature store para ML (não há modelos de ML no escopo)
  ✗ Multi-tenant (isolamento por schema não é necessário para um único cliente)
```


---

## 8. Checklist de Code Review / Auditoria

- [ ] **Segurança**: `.env` no `.gitignore`? Segredos no Secret Manager (prod)?
- [ ] **SSL**: `DB_SSLMODE=require` em produção? `REQUESTS_CA_BUNDLE` para proxy?
- [ ] **Migrações**: Backup antes da 004? `pg_dump` testado?
- [ ] **Idempotência**: `main.py` re-executável? `dbt build` re-executável?
- [ ] **Testes**: `pytest` passa local? `dbt build` passa local?
- [ ] **Monitoramento**: `bronze.scrape_runs` consultado? Alertas configurados?
- [ ] **Documentação**: `README.md` atualizado (banner histórico)? Diagramas Mermaid renderizam?
- [ ] **Performance**: Índices em `chave_conteudo`, `origem`, `data_coleta`?
- [ ] **Limpeza**: `bronze.job_observations` removida (migração 005 aplicada)?

---

## 9. Execução Rápida

```bash
# 1. Setup
git clone https://github.com/Willian-Cruz/hub_vagas.git
cd hub_vagas
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# 2. Config
cp .env.example .env
# edite .env com credenciais PostgreSQL

# 3. Migrações (se banco existente)
psql -h localhost -p 5432 -U usuario -d hub_vagas -f infra/migrations/004_jobs_novos_campos.sql

# 4. Pipeline completo
python app/main.py           # Ingestão → raw + bronze
python app/transform.py      # dbt build → bronze → silver → gold
python app/export_excel.py   # Gera data/exports/vagas.xlsx

# 5. Agendado (produção)
python app/scheduler.py --com-transformacao  # Diário 06:00 + dbt auto

# 6. Testes
python -m pytest app/tests/ -v
```

---

> **Nota:** Este documento deve ser mantido sincronizado com a evolução do código. Atualize ao adicionar portais, alterar schemas, ou mudar padrões arquiteturais. O `README.md` mantém o histórico detalhado (etapas 1 a 15) e está marcado como histórico a partir da versão 06/11/2026.
