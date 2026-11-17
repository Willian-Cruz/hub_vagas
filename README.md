# Hub Vagas — Job Market Analytics

[![CI Hub Vagas](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml/badge.svg)](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy-336791?logo=postgresql&logoColor=white)
![Playwright](https://img.shields.io/badge/Coleta-Playwright-2EAD33?logo=playwright&logoColor=white)
![dbt](https://img.shields.io/badge/Transforma%C3%A7%C3%A3o-dbt-FF694B?logo=dbt&logoColor=white)
![Power BI](https://img.shields.io/badge/Dashboard-Power%20BI-F2C811?logo=powerbi&logoColor=black)
![License](https://img.shields.io/badge/licen%C3%A7a-MIT-lightgrey)

Pipeline de dados que coleta vagas de Dados e Tecnologia em portais brasileiros e as organiza em camadas no PostgreSQL seguindo a **arquitetura medallion**:

- **Raw** — tabela `jobs`: dados brutos inseridos diretamente pelos scrapers (landing zone, dedup por link / origem+id_externo).
- **Bronze** — `bronze.scrape_runs`: snapshots append-only de execução por fonte (monitoramento).
- **Silver** — `silver.jobs`: normalização, deduplicação avançada e limpeza a partir da raw.
- **Gold** — `gold.mart_*`: matérias-analíticos a partir do Silver.

O Python (via `main.py`) é responsável **apenas pela ingestão** (scrape → raw `jobs`). A transformação é responsabilidade do **dbt** (via `transform.py`), que move os dados da raw para Bronze, Silver e Gold. A exportação para Excel e o dashboard no Power BI consomem a Gold.

A execução é em **lote (batch)**: uma vez por dia via APScheduler, ou manualmente.

---

## Arquitetura

```mermaid
flowchart LR
    A[Portais de vagas<br/>Vagas.com · InfoJobs · Gupy] --> B[Scrapers<br/>Playwright / requests + BeautifulSoup<br/>filtro de relevância]
    B --> C[(Raw<br/>tabela jobs - landing zone)]
    C -->|dbt build| D[Bronze<br/>scrape_runs - snapshots]
    D -->|dbt build| E[Silver<br/>NULL · padronização · deduplicação]
    E -->|dbt build| F[Gold<br/>marts analíticos]
    F --> G[Exportação<br/>Excel .xlsx]
    G --> H[Dashboard<br/>Power BI]
```

| Etapa | Onde fica | O que faz |
| --- | --- | --- |
| **Ingestão** | `app/main.py`, `app/services/pipeline_service.py`, `app/services/collector_service.py` | Roda cada scraper em sequência (a falha de um não interrompe os outros), grava vagas brutas na tabela raw `jobs` (dedup por link / origem+id_externo) e registra status de execução em `bronze.scrape_runs`. Sem normalização de negócio. |
| **Relevância** | `app/services/relevance_service.py` | No Vagas.com e no InfoJobs, descarta a vaga cujo **título** não cita nenhum termo de dados (palavra inteira). A contagem de descartadas vai para o log e para as métricas. |
| **Raw** | `app/database/job_model.py`, `app/repositories/job_repository.py` | Tabela `jobs` (schema público): landing zone com dados brutos dos scrapers. Duplicada = mesmo link, ou mesmo ID no portal (`origem` + `id_externo`). |
| **Bronze** | `dbt/models/staging/`, `dbt/models/marts/mart_status_fontes.sql` | Executado via `python app/transform.py`. Snapshot imutável de execução por fonte em `bronze.scrape_runs` para monitoramento de freshness. |
| **Silver** | `dbt/models/intermediate/jobs.sql`, `dbt/macros/` | Executado via `python app/transform.py`. Campo sem informação é `NULL`, nunca "Não informado". Padroniza senioridade, localidade e modalidade, identifica o salário divulgado e mantém uma vaga por ID no portal. A mesma vaga republicada com outro ID é juntada (portal + título + empresa + local). |
| **Gold** | `dbt/models/marts/` | Executado via `python app/transform.py`. `mart_vagas` (base do Excel), `mart_vagas_por_dia`, `mart_vagas_por_origem_localidade`, `mart_demanda_tecnologias` e `mart_status_fontes`. |
| **Orquestração** | `app/main.py`, `app/scheduler.py`, `app/services/scheduler_service.py` | Apenas ingestão: coleta e gravação na raw `jobs`. A transformação é disparada separadamente via `transform.py`. |
| **Transformação** | `app/transform.py`, `app/run_dbt.py` | Ponto de entrada para o dbt. Executa `dbt build` que move dados da raw para Bronze → Silver → Gold. |
| **Exportação** | `app/services/export_service.py`, `app/export_excel.py` | Gera `data/exports/vagas.xlsx` a partir de `gold.mart_vagas`. |

---

## Modelo de dados

A tabela `jobs` (raw) é mantida pelo SQLAlchemy. O schema `bronze` (`scrape_runs`) é mantido pelo SQLAlchemy. A Silver (`silver.jobs`) e a Gold (`gold.mart_*`) são criadas pelo dbt.

```mermaid
erDiagram
    scrape_runs {
        uuid run_id PK
        string source PK
        string status
        int pages_processed
        int jobs_found
        string error
        datetime started_at
        datetime finished_at
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

Fluxo de transformação pelo dbt:

```mermaid
flowchart LR
    Raw[(jobs<br/>raw layer)] --> Bronze[(bronze.scrape_runs<br/>monitoramento)]
    Bronze --> Silver[(silver.jobs<br/>normalização + dedupe)]
    Silver --> Gold[(gold.mart_*<br/>analytics)]
    Gold --> Excel[Excel .xlsx]
    Gold --> BI[Power BI]
```

---

## Estrutura detalhada de cada camada

### Raw — `public.jobs` (landing zone)

Uma linha por vaga, dedup por `link` (UNIQUE) e por `(origem, id_externo)`.

| Coluna | Tipo | Restrição |
| --- | --- | --- |
| `id` | int | PK |
| `titulo` | string | — |
| `empresa` | string | — |
| `senioridade` | string | — |
| `localizacao` | string | — |
| `descricao` | text | — |
| `salario` | string | — |
| `link` | string | UK, NOT NULL |
| `origem` | string | — |
| `data_coleta` | datetime | NOT NULL, default `now()` |
| `id_externo` | string | — |
| `data_publicacao` | datetime | — |
| `modalidade` | string | — |
| `experiencia` | string | — |
| `escolaridade` | string | — |
| `qtd_posicoes` | int | — |
| `chave_conteudo` | string | index |

### Bronze — `bronze.scrape_runs` (monitoramento de execução)

Snapshot append-only de execução por fonte.

| Coluna | Tipo | Restrição |
| --- | --- | --- |
| `run_id` | uuid | PK (composto com `source`) |
| `source` | string | PK (composto com `run_id`) |
| `status` | string | NOT NULL |
| `pages_processed` | int | NOT NULL, default 0 |
| `jobs_found` | int | NOT NULL, default 0 |
| `error` | text | — |
| `started_at` | datetime | NOT NULL |
| `finished_at` | datetime | NOT NULL |
| `created_at` | datetime | NOT NULL, default `now()` |

### Silver — `silver.jobs` (normalização + dedupe)

Uma vaga por portal e identificador, campo sem informação é `NULL`.

| Coluna | Tipo | Restrição |
| --- | --- | --- |
| `raw_job_id` | int | — |
| `origem` | string | — |
| `link` | string | — |
| `id_externo` | string | — |
| `titulo` | string | — |
| `empresa` | string | — |
| `senioridade` | string | — |
| `localizacao` | string | — |
| `descricao` | text | — |
| `salario` | string | — |
| `modalidade` | string | — |
| `experiencia` | string | — |
| `escolaridade` | string | — |
| `qtd_posicoes` | int | — |
| `data_publicacao` | datetime | — |
| `chave_conteudo` | string | — |
| `data_coleta` | datetime | — |

### Gold — `gold.mart_vagas` (exportação + Power BI)

Vagas Silver enriquecidas com tecnologias.

| Coluna | Tipo | Restrição |
| --- | --- | --- |
| `id` | int | PK |
| `titulo` | string | — |
| `empresa` | string | — |
| `senioridade` | string | — |
| `localizacao` | string | — |
| `salario` | string | — |
| `modalidade` | string | — |
| `experiencia` | string | — |
| `escolaridade` | string | — |
| `qtd_posicoes` | int | — |
| `origem` | string | — |
| `id_externo` | string | — |
| `link` | string | — |
| `descricao` | text | — |
| `data_publicacao` | datetime | — |
| `data_coleta` | datetime | — |
| `tecnologias` | string | agregação `string_agg` das tecnologias monitoradas |

## Regras de dados

- **Campo sem informação é `NULL`.** Os scrapers do Vagas.com e do InfoJobs já devolvem `None` para "Confidencial", "Localização não informada" e similares, e a Silver trata os mesmos textos vindos de qualquer fonte. No Power BI, trate `NULL` como "(Em branco)".
- **Relevância.** Os portais buscam por palavras soltas, então "engenheiro de dados" também devolve engenharia civil e vendas. A vaga só passa se o título citar um termo de `RelevanceService.TERMOS_TITULO` (dados, data, analytics, BI, ETL, dbt, SQL, Python, Spark, Airflow, Databricks, Snowflake, BigQuery e outros), como palavra inteira. As descartadas não chegam ao raw; só a contagem é registrada. A Gupy busca por termos próprios e ainda não passa por esse filtro.
- **Deduplicação.** Na raw `jobs`: dedup por `link` (UNIQUE) e por `(origem, id_externo)`. Na Silver: uma vaga por `id_externo` (sem ele, pelo link), mantendo a observação mais recente, e uma vaga por portal + título + empresa + local, sem acento nem diferença de caixa. A chave de conteúdo só existe quando empresa e local são conhecidos, para não juntar vagas diferentes.
- **Senioridade.** O nível do portal tem prioridade. Sem ele, o `seniority_service` testa as evidências abaixo, em ordem, e fica com a primeira que acerta:
  1. palavra de nível no título (mesma regra do `NormalizeService`, com algumas palavras a mais, como `mid-level` e `intern`, e sem ler "PL/SQL" ou "PL-300" como Pleno);
  2. nível escrito na descrição, como "Nível: Pleno" ou "Analista de Dados Sênior";
  3. campo de experiência do portal: menos de 3 anos é Júnior, de 3 a 4 é Pleno e 5 ou mais é Sênior ("Sem experiência" é Júnior e "Só estágios" é Estágio/Trainee);
  4. "N anos de experiência" na descrição, pela mesma faixa.

  Sem nenhuma evidência, o campo fica `NULL`. Hoje o InfoJobs usa a cascata inteira; o parser da Catho usa só o título, porque o card não traz descrição nem experiência. A origem da decisão (`titulo`, `descricao_nivel`, `experiencia_campo` ou `descricao_anos`) vai em `senioridade_origem`, dentro do `source_payload` do raw. Valores: Estágio/Trainee, Júnior, Pleno, Sênior, Especialista, Coordenador, Liderança, Diretoria e Técnico (este só quando o portal informa).
- **Modalidade.** Remoto, Híbrido ou Presencial. Quando o portal não informa, vem da localização ("Home Office" vira Remoto).
- **Salário.** Vem do portal; sem ele, de um valor `R$` na descrição; "A combinar" quando o texto indica. O card do Vagas.com não traz salário.
- **Datas.** `data_publicacao` é a data do portal (o Vagas.com informa "Há N dias", então a precisão é de dia; o InfoJobs informa a data exata). `data_coleta` é o momento da coleta.

---

## Estrutura do projeto

```text
hub_vagas/
├── .github/workflows/
│   └── tests.yml              # CI: roda o pytest a cada push e PR na main
├── app/
│   ├── config/settings.py     # leitura do .env
│   ├── constants/selectors.py # seletores CSS dos portais
│   ├── database/              # conexão e modelos SQLAlchemy (raw jobs, bronze scrape_runs)
│   ├── repositories/          # bronze_repository, job_repository
│   ├── schemas/job_schema.py  # validação Pydantic
│   ├── scrapers/              # base_scraper, vagas_scraper, infojobs_scraper, gupy_scraper,
│   │                          # catho_parser, parser_utils
│   ├── services/              # collector, export, job, normalize, pipeline,
│   │                          # relevance, salary, scheduler, seniority, tech
│   ├── tests/                 # testes + conftest.py (banco mockado) + fixtures/ (HTML real dos portais)
│   ├── utils/                 # logger (rotação de arquivo), text_utils, date_utils
│   ├── debug_vagas.py         # diagnóstico visual do scraper do Vagas.com
│   ├── export_excel.py        # ponto de entrada da exportação
│   ├── main.py                # INGESTÃO: scrape → raw `jobs`
│   ├── transform.py           # TRANSFORMAÇÃO: dbt build (raw → Bronze → Silver → Gold)
│   ├── run_dbt.py             # CLI dbt com credenciais carregadas do .env
│   └── scheduler.py           # execução agendada da ingestão
├── check_catho.py             # verificação de qualidade dos dados da Catho
├── check_data_quality.py      # verificação geral de qualidade de dados
├── check_gold_tech.py         # verificação de tecnologias na camada Gold
├── check_nulls.py             # verificação de campos NULL
├── check_silver_catho.py      # verificação específica da Silver para Catho
├── check_values.py            # verificação de valores válidos
├── dbt/
│   ├── macros/                # normalização de campos, tecnologias monitoradas, nomes de schema, select_raw_jobs
│   ├── models/                # sources.yml (raw + bronze), staging/, intermediate/ (Silver) e marts/ (Gold)
│   ├── tests/                 # testes de dados: unicidade da Silver e contrato de NULL
│   ├── dbt_project.yml
│   └── profiles.yml.example   # perfil sem segredos
├── infra/migrations/          # SQL para bancos criados por versões anteriores (001 a 004)
├── .env.example
├── requirements.txt
└── LICENSE
```

---

## Portais

| Portal | Coleta | Situação |
| --- | --- | --- |
| Vagas.com | Playwright (scroll infinito) + BeautifulSoup | Implementado: ID, data de publicação, posições, local, nível e descrição do card. Salário só na página de detalhe |
| InfoJobs | requests + BeautifulSoup, paginado | Implementado: salário, experiência, escolaridade, modalidade, data exata, ID e senioridade em cascata (título, descrição e experiência) |
| Gupy | Playwright + BeautifulSoup, por termos de busca | Implementado, com calibração de seletores pendente (`app/scrapers/gupy_scraper.py`). Ainda não usa o filtro de relevância nem devolve `NULL`; a Silver trata os textos "Não informado" |
| Catho | — | Parser dos cards pronto e testado com HTML real (`app/scrapers/catho_parser.py`): empresa, local, posições, salário, data e senioridade pelo título. Falta o scraper (busca, paginação e coleta). Scripts de verificação de qualidade: `check_catho.py`, `check_silver_catho.py` |
| Remotar, Sólides | — | Próximos (mesmo contrato dos scrapers atuais) |
| LinkedIn, Indeed, Glassdoor | — | Planejados |

---

## Tecnologias identificadas nas descrições

18 termos monitorados em `dbt/macros/monitored_technologies.sql` (Gold): Python, SQL, AWS, Azure, GCP, Spark, Airflow, Kafka, Docker, Kubernetes, PostgreSQL, MySQL, Oracle, MongoDB, Power BI, Tableau, Databricks e Snowflake.

---

## Como executar

### 1. Instalação

```bash
git clone https://github.com/Willian-Cruz/hub_vagas.git
cd hub_vagas
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt  # inclui o dbt-postgres
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

Se o InfoJobs não conseguir validar o certificado TLS em uma rede com proxy corporativo, configure `REQUESTS_CA_BUNDLE` com o caminho do certificado CA fornecido pela rede. A validação TLS continua habilitada.

Na configuração local (`DB_*`), `main.py` cria o banco se ele ainda não existir e depois cria as tabelas. O usuário PostgreSQL configurado precisa ter o privilégio `CREATEDB`. Em uma conexão remota via `DATABASE_URL`, crie o banco no provedor antes de executar o pipeline.

A variável opcional `DB_SSLMODE` (por exemplo, `require`) é lida apenas pelo dbt. Para o restante da aplicação em bancos que exigem TLS, use `DATABASE_URL` com `?sslmode=require`; o `run_dbt.py` também lê o `sslmode` dessa URL.

### 3. Migrações

`create_all()` não altera tabelas já existentes. Para bancos criados por versões anteriores, aplique as migrações de `infra/migrations` em ordem:

| Migração | O que faz |
| --- | --- |
| `001` | Adiciona a chave da tabela de associação `job_technologies`. Interrompe se encontrar pares duplicados |
| `002` | Adiciona `jobs.data_coleta`. Vagas antigas recebem o momento da migração, pois a versão anterior não guardava esse timestamp |
| `003` | Cria o schema `bronze` com `scrape_runs` (`main.py` e `scheduler.py` também os criam automaticamente) |
| `004` | Adiciona em `jobs` os campos `id_externo`, `data_publicacao`, `modalidade`, `experiencia`, `escolaridade`, `qtd_posicoes` e `chave_conteudo`; preenche `id_externo` a partir dos links já gravados; troca os textos "Não informado", "Confidencial" e "Localização Não Informada" por `NULL`; cria o índice único `(origem, id_externo)` |
| `005` | Remove a tabela obsoleta `bronze.job_observations` (não lida por nenhum consumidor; o dbt lê direto da raw `jobs`) |

A `004` é idempotente e **interrompe** se houver o mesmo ID repetido no mesmo portal. Faça um backup antes de aplicá-la:

```bash
# use os valores de DB_USER, DB_NAME, DB_HOST e DB_PORT do seu .env
# (no PowerShell, prefira -f a ">": o redirecionamento grava em UTF-16)
pg_dump -h localhost -p 5432 -U usuario -d hub_vagas -f backup_antes_da_004.sql
psql -h localhost -p 5432 -U usuario -d hub_vagas -f infra/migrations/004_jobs_novos_campos.sql
```

Com uma `DATABASE_URL` completa (banco remoto), passe a URL entre aspas no lugar dos parâmetros: `pg_dump "postgresql://usuario:senha@host:5432/banco" -f backup.sql`.

### 4. Pipeline — Ingestão e Transformação (etapas separadas)

#### 4a. Ingestão: coleta → raw `jobs`

```bash
# Execução única: coleta vagas e grava na tabela raw `jobs`
python app/main.py

# Execução agendada: todo dia às 06:00, horário de São Paulo (padrão)
python app/scheduler.py

# Horário customizado (ex: 08:30)
python app/scheduler.py --hora 8 --minuto 30

# Modo intervalo — útil para testes (ex: a cada 2 horas)
python app/scheduler.py --intervalo 2

# Ingestão com transformação dbt após cada coleta bem-sucedida
python app/scheduler.py --com-transformacao
```

#### 4b. Transformação: raw → Bronze → Silver → Gold (via dbt)

```bash
# Executa dbt build: modelos + testes
python app/transform.py

# Apenas verificar frescor das fontes
python app/transform.py source freshness

# Ou diretamente via run_dbt.py
python app/run_dbt.py build
python app/run_dbt.py debug
python app/run_dbt.py source freshness
```

O dbt só roda quando o raw foi gravado com sucesso. Exemplo de log de ingestão (os números são ilustrativos):

```text
PIPELINE DE INGESTÃO INICIADO
Etapa 1/3: Coletando vagas...
Coletadas: 87 vagas | Descartadas (fora do tema): 214
Fonte Vagas.com: success | Vagas: 41 | Páginas: 20
Fonte InfoJobs: success | Vagas: 30 | Páginas: 10
Fonte Gupy: success | Vagas: 16 | Páginas: 12
Etapa 2/3: Gravando vagas na raw layer `jobs`...
Raw concluída — 54 salvas, 33 duplicadas, 0 erros
Etapa 3/3: Gravando status de execução no Bronze...
Bronze concluída — 3 scrape_run(s) registrado(s)
PIPELINE CONCLUÍDO em 45.2s | Coletadas: 87 | Descartadas: 214 | Raw: 54 salvas / 33 dup / 0 err
```

Exemplo de log de transformação:

```text
Executando transformação de dados via dbt...
[dbt output...]
Transformação concluída com sucesso!
```

Os logs ficam em `logs/pipeline.log`, com rotação a cada 5 MB (3 backups).

### 5. Camadas dbt

O `app/run_dbt.py` lê o `.env` e configura a conexão a partir de `DATABASE_URL` ou das variáveis `DB_*`. O perfil sem segredos é copiado de `dbt/profiles.yml.example` para o arquivo local ignorado `dbt/profiles.yml`. O `build` cria os schemas `silver` e `gold`, então o usuário do PostgreSQL precisa ter permissão para criar schemas e tabelas. As fontes são declaradas em `dbt/models/sources.yml`.

| Camada | Origem | Modelos | Materialização |
| --- | --- | --- | --- |
| Raw | scrapers → `jobs` | tabela `jobs` (schema público) | tabela |
| Bronze | `bronze.scrape_runs` | tabela `scrape_runs` (schema bronze) | tabela |
| Silver | raw `jobs` → `silver.jobs` | `stg_*`, `jobs` | view / tabela |
| Gold | Silver → `gold.mart_vagas` | `mart_vagas` | tabela |

Os demais marts Gold (`mart_vagas_por_dia`, `mart_vagas_por_origem_localidade`, `mart_demanda_tecnologias`, `mart_status_fontes`) estão planejados para remoção; as visualizações serão construídas diretamente no Power BI.

Além dos testes declarados nos `.yml` (não nulo, único, valores aceitos), há testes em `dbt/tests/` que protegem a Silver: sem ID repetido no mesmo portal, sem vaga repetida por conteúdo e sem o texto "Não informado" nos campos.

### 6. Exportação para Excel / Power BI

```bash
cd app
python export_excel.py
```

Gera `data/exports/vagas.xlsx` a partir de `gold.mart_vagas`, que alimenta o dashboard no Power BI. As colunas são `id`, `titulo`, `empresa`, `senioridade`, `localizacao`, `salario`, `modalidade`, `experiencia`, `escolaridade`, `qtd_posicoes`, `origem`, `id_externo`, `link`, `descricao`, `data_publicacao`, `data_coleta` e `tecnologias`. As datas saem no horário de São Paulo, sem fuso.

Execute `python app/main.py` e depois `python app/transform.py` antes de exportar.

---

## Testes

```bash
cd app
pytest tests/ -v
```

Se o `pytest` do venv não for encontrado (acontece quando a pasta do projeto muda de lugar), use `python -m pytest tests/ -v`.

A suíte usa um mock global do banco (`conftest.py`), então roda sem PostgreSQL. Os testes cobrem scrapers, normalização, senioridade, salário, repositórios (inclusive deduplicação por ID e conteúdo e a gravação raw), relevância, pipeline, agendamento, exportação, `run_dbt` e configuração. Os parsers do Vagas.com, do InfoJobs e da Catho também são testados contra **HTML real** dos portais (`app/tests/fixtures/`); quando um portal mudar o layout, salve os cards novos ali e ajuste os testes do portal (`test_parsers_html_real.py`, `test_infojobs_scraper_nov2026.py` ou `test_catho_parser.py`). Instale as dependências com `pip install -r requirements.txt` antes de executá-los.

O GitHub Actions roda o `pytest` a cada push e pull request na `main`. O `dbt build` não roda no CI porque precisa de um PostgreSQL; execute-o localmente com `python app/transform.py` ou `python app/run_dbt.py build`.

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
| 11 | Camadas Bronze, Silver e Gold: coleta append-only em JSONB, transformações e testes de dados com dbt, exportação a partir do mart Gold e tabela `jobs` mantida como legado |
| 12 (nov/2026) | Revisão dos scrapers do Vagas.com e InfoJobs com HTML real: campos vazios viram `NULL`, novos campos, filtro de relevância, deduplicação por ID e conteúdo (migração `004`). No dbt, `NULL`, campos novos e deduplicação na Silver. Correções na gravação Bronze, no `run_dbt.py` e na exportação para Excel |
| 13 (nov/2026) | Senioridade em cascata (portal, título, descrição e experiência), com a origem registrada na Bronze; parser da Catho testado com HTML real; correções no InfoJobs: modalidade lida pelos três ícones do card (antes só "Presencial") e fragmento HTML original preservado na Bronze |
| 14 (nov/2026) | **Arquitetura medallion com `jobs` como raw**: `main.py` executa apenas scrape → raw `jobs`; `transform.py` executa dbt build (raw → Bronze → Silver → Gold); `scheduler.py` desacoplado do dbt; `PipelineService` grava na raw `jobs` e em `bronze.scrape_runs`; dbt lê da raw `jobs` (não mais do JSONB do Bronze) |
| 15 (nov/2026) | Coleta e parser da Catho com HTML real, senioridade por título, staging `stg_catho_jobs` no dbt, scripts de verificação de qualidade (`check_*.py`), ajustes na macro `classify_seniority_cascade` e testes de NULL na Silver |

---

## Próximos passos

- Calibrar os seletores do scraper da Gupy e aplicar a ele o filtro de relevância, o contrato de `NULL` e a cascata de senioridade
- Corrigir a senioridade lida pelo pipeline (`NormalizeService` e macro `normalize_seniority`): "PL/SQL" e "PL-300" viram Pleno, e o rótulo "Liderança" não é reconhecido quando já vem pronto do scraper
- Buscar a página de detalhe da vaga (descrição completa e salário) nos portais que só mostram um resumo no card; a senioridade inferida pela descrição também ganha com isso
- Transformar o parser da Catho em scraper (busca, paginação, coleta), adicionar Remotar e Sólides, e depois LinkedIn, Indeed e Glassdoor
- Migrar o `AnalyticsService` para a Gold e aposentar a tabela `jobs`
- Publicar prints do dashboard do Power BI neste README

---

## Autor

**Willian da Cruz** — projeto de estudo e portfólio em Engenharia de Dados.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-williandacruz-0A66C2?logo=linkedin)](https://www.linkedin.com/in/williandacruz/)
[![GitHub](https://img.shields.io/badge/GitHub-Willian--Cruz-181717?logo=github)](https://github.com/Willian-Cruz)

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).