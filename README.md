# Hub Vagas — Job Market Analytics

[![CI Hub Vagas](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml/badge.svg)](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy-336791?logo=postgresql&logoColor=white)
![Playwright](https://img.shields.io/badge/Coleta-Playwright-2EAD33?logo=playwright&logoColor=white)
![dbt](https://img.shields.io/badge/Transforma%C3%A7%C3%A3o-dbt-FF694B?logo=dbt&logoColor=white)
![Power BI](https://img.shields.io/badge/Dashboard-Power%20BI-F2C811?logo=powerbi&logoColor=black)
![License](https://img.shields.io/badge/licen%C3%A7a-MIT-lightgrey)

Pipeline de dados que coleta vagas de Dados e Tecnologia em portais brasileiros e as organiza em camadas no PostgreSQL. O Python captura os registros na camada **Bronze** (JSONB, append-only); o **dbt** padroniza e deduplica na **Silver** e publica os marts na **Gold**. A exportação para Excel e o dashboard no Power BI consomem a Gold. A tabela `jobs` continua sendo mantida durante a transição e ainda alimenta o `AnalyticsService`.

A execução é em **lote (batch)**: uma vez por dia via APScheduler, ou manualmente.

---

## Arquitetura

```mermaid
flowchart LR
    A[Portais de vagas<br/>Vagas.com · InfoJobs · Gupy] --> B[Scrapers<br/>Playwright / requests + BeautifulSoup<br/>filtro de relevância]
    B --> C[(Bronze<br/>PostgreSQL JSONB)]
    C --> D[dbt Silver<br/>NULL · padronização · deduplicação]
    D --> E[dbt Gold<br/>marts analíticos]
    E --> F[Exportação<br/>Excel .xlsx]
    F --> G[Dashboard<br/>Power BI]
    B -.-> L[(jobs legado<br/>transição)]
    L -.-> H[AnalyticsService]
```

| Etapa | Onde fica | O que faz |
| --- | --- | --- |
| Coleta | `app/scrapers/`, `app/services/collector_service.py` | Roda cada scraper em sequência (a falha de um não interrompe os outros) e devolve um `ScrapeResult` por fonte, com status, páginas, erro e vagas. Preserva o fragmento HTML de cada card |
| Relevância | `app/services/relevance_service.py` | No Vagas.com e no InfoJobs, descarta a vaga cujo **título** não cita nenhum termo de dados (palavra inteira). A contagem de descartadas vai para o log e para as métricas |
| Bronze | `app/database/bronze_model.py`, `app/repositories/bronze_repository.py` | Grava uma observação por vaga e por execução em `bronze.job_observations` (JSONB, append-only, com `run_id` e hash) e o status de cada fonte em `bronze.scrape_runs`, inclusive fontes vazias ou com falha. O payload é a saída do scraper, sem normalização de negócio |
| Silver | `dbt/models/staging/`, `dbt/models/intermediate/jobs.sql`, `dbt/macros/` | Campo sem informação é `NULL`, nunca "Não informado". Padroniza senioridade, localidade e modalidade, identifica o salário divulgado e mantém uma vaga por ID no portal. A mesma vaga republicada com outro ID é juntada (portal + título + empresa + local) |
| Gold | `dbt/models/marts/` | `mart_vagas` (base do Excel), `mart_vagas_por_dia`, `mart_vagas_por_origem_localidade`, `mart_demanda_tecnologias` e `mart_status_fontes` |
| Legado | `app/repositories/job_repository.py`, `app/services/analytics_service.py` | Mantém a tabela `jobs` durante a transição, só quando a Bronze foi gravada. Duplicada = mesmo link, ou mesmo ID no portal (`origem` + `id_externo`), ou mesmo conteúdo. Ao reencontrar a vaga, só preenche campos `NULL`; nunca sobrescreve |
| Orquestração | `app/services/pipeline_service.py`, `app/main.py`, `app/scheduler.py`, `app/services/scheduler_service.py` | Executa coleta, Bronze e legado, registra métricas (coletadas, descartadas, Bronze, salvas, duplicadas, erros, duração) e roda o dbt |
| Exportação | `app/services/export_service.py`, `app/export_excel.py` | Gera `data/exports/vagas.xlsx` a partir de `gold.mart_vagas` |

## Modelo de dados

A Bronze e a tabela legada `jobs` são tabelas do SQLAlchemy. A Silver (`silver.jobs`) e a Gold (`gold.mart_*`) são criadas pelo dbt.

```mermaid
erDiagram
    scrape_runs ||--o{ job_observations : registra
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

## Regras de dados

- **Campo sem informação é `NULL`.** Os scrapers do Vagas.com e do InfoJobs já devolvem `None` para "Confidencial", "Localização não informada" e similares, e a Silver trata os mesmos textos vindos de qualquer fonte. No Power BI, trate `NULL` como "(Em branco)".
- **Relevância.** Os portais buscam por palavras soltas, então "engenheiro de dados" também devolve engenharia civil e vendas. A vaga só passa se o título citar um termo de `RelevanceService.TERMOS_TITULO` (dados, data, analytics, BI, ETL, dbt, SQL, Python, Spark, Airflow, Databricks, Snowflake, BigQuery e outros), como palavra inteira. As descartadas não chegam à Bronze; só a contagem é registrada. A Gupy busca por termos próprios e ainda não passa por esse filtro.
- **Deduplicação.** Na Silver: uma vaga por `id_externo` (sem ele, pelo link), mantendo a observação mais recente, e uma vaga por portal + título + empresa + local, sem acento nem diferença de caixa. A chave de conteúdo só existe quando empresa e local são conhecidos, para não juntar vagas diferentes. Na tabela `jobs` valem as regras da etapa Legado.
- **Senioridade.** O nível do portal tem prioridade. Sem ele, é inferido do título. Valores: Estágio/Trainee, Júnior, Pleno, Sênior, Especialista, Coordenador, Liderança, Diretoria e Técnico (este só quando o portal informa).
- **Modalidade.** Remoto, Híbrido ou Presencial. Quando o portal não informa, vem da localização ("Home Office" vira Remoto).
- **Salário.** Vem do portal; sem ele, de um valor `R$` na descrição; "A combinar" quando o texto indica. O card do Vagas.com não traz salário.
- **Datas.** `data_publicacao` é a data do portal (o Vagas.com informa "Há N dias", então a precisão é de dia; o InfoJobs informa a data exata). `data_coleta` é o momento da coleta. Na tabela `jobs`, a `data_coleta` anterior à migração `002` não é confiável (todas recebem o horário da migração); use `data_publicacao`.

---

## Estrutura do projeto

```text
hub_vagas/
├── .github/workflows/
│   └── tests.yml              # CI: roda o pytest a cada push e PR na main
├── app/
│   ├── config/settings.py     # leitura do .env
│   ├── constants/selectors.py # seletores CSS dos portais
│   ├── database/              # conexão e modelos SQLAlchemy (Bronze e tabelas legadas)
│   ├── repositories/          # bronze_repository, job_repository, tech_repository
│   ├── schemas/job_schema.py  # validação Pydantic
│   ├── scrapers/              # base_scraper, vagas_scraper, infojobs_scraper, gupy_scraper
│   ├── services/              # analytics, collector, export, job, normalize, pipeline,
│   │                          # relevance, salary, scheduler, tech
│   ├── tests/                 # testes + conftest.py (banco mockado) + fixtures/ (HTML real dos portais)
│   ├── utils/                 # logger (rotação de arquivo), text_utils, date_utils
│   ├── debug_vagas.py         # diagnóstico visual do scraper do Vagas.com
│   ├── export_excel.py        # ponto de entrada da exportação
│   ├── main.py                # execução única do pipeline (inclui o dbt)
│   ├── run_dbt.py             # CLI dbt com credenciais carregadas do .env
│   └── scheduler.py           # execução agendada
├── dbt/
│   ├── macros/                # normalização de campos, tecnologias monitoradas, nomes de schema
│   ├── models/                # sources.yml, staging/, intermediate/ (Silver) e marts/ (Gold)
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
| InfoJobs | requests + BeautifulSoup, paginado | Implementado: salário, experiência, escolaridade, modalidade, data exata e ID |
| Gupy | Playwright + BeautifulSoup, por termos de busca | Implementado, com calibração de seletores pendente (`app/scrapers/gupy_scraper.py`). Ainda não usa o filtro de relevância nem devolve `NULL`; a Silver trata os textos "Não informado" |
| Catho, Remotar, Sólides | — | Próximos (mesmo contrato dos scrapers atuais) |
| LinkedIn, Indeed, Glassdoor | — | Planejados |

## Tecnologias identificadas nas descrições

18 termos monitorados em `app/services/tech_service.py` (tabela `jobs`) e em `dbt/macros/monitored_technologies.sql` (Gold): Python, SQL, AWS, Azure, GCP, Spark, Airflow, Kafka, Docker, Kubernetes, PostgreSQL, MySQL, Oracle, MongoDB, Power BI, Tableau, Databricks e Snowflake.

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

Se o InfoJobs não conseguir validar o certificado TLS em uma rede com proxy
corporativo, configure `REQUESTS_CA_BUNDLE` com o caminho do certificado CA
fornecido pela rede. A validação TLS continua habilitada.

Na configuração local (`DB_*`), `main.py` cria o banco se ele ainda não existir
e depois cria as tabelas. O usuário PostgreSQL configurado precisa ter o
privilégio `CREATEDB`. Em uma conexão remota via `DATABASE_URL`, crie o banco
no provedor antes de executar o pipeline.

A variável opcional `DB_SSLMODE` (por exemplo, `require`) é lida apenas pelo dbt.
Para o restante da aplicação em bancos que exigem TLS, use `DATABASE_URL` com
`?sslmode=require`; o `run_dbt.py` também lê o `sslmode` dessa URL.

### 3. Migrações

`create_all()` não altera tabelas já existentes. Para bancos criados por versões
anteriores, aplique as migrações de `infra/migrations` em ordem:

| Migração | O que faz |
| --- | --- |
| `001` | Adiciona a chave da tabela de associação `job_technologies`. Interrompe se encontrar pares duplicados |
| `002` | Adiciona `jobs.data_coleta`. Vagas antigas recebem o momento da migração, pois a versão anterior não guardava esse timestamp |
| `003` | Cria o schema `bronze` com `scrape_runs` e `job_observations` (`main.py` e `scheduler.py` também os criam automaticamente) |
| `004` | Adiciona em `jobs` os campos `id_externo`, `data_publicacao`, `modalidade`, `experiencia`, `escolaridade`, `qtd_posicoes` e `chave_conteudo`; preenche `id_externo` a partir dos links já gravados; troca os textos "Não informado", "Confidencial" e "Localização Não Informada" por `NULL`; cria o índice único `(origem, id_externo)` |

A `004` é idempotente e **interrompe** se houver o mesmo ID repetido no mesmo
portal. Faça um backup antes de aplicá-la:

```bash
# use os valores de DB_USER, DB_NAME, DB_HOST e DB_PORT do seu .env
# (no PowerShell, prefira -f a ">": o redirecionamento grava em UTF-16)
pg_dump -h localhost -p 5432 -U usuario -d hub_vagas -f backup_antes_da_004.sql
psql -h localhost -p 5432 -U usuario -d hub_vagas -f infra/migrations/004_jobs_novos_campos.sql
```

Com uma `DATABASE_URL` completa (banco remoto), passe a URL entre aspas no lugar
dos parâmetros: `pg_dump "postgresql://usuario:senha@host:5432/banco" -f backup.sql`.

### 4. Pipeline

```bash
# Execução única: coleta, Bronze, tabela legada jobs e dbt build.
# Sai com código 1 se a coleta/persistência ou os modelos/testes dbt falharem.
python app/main.py

# Execução agendada: todo dia às 06:00, horário de São Paulo (padrão).
# Sem --com-dbt, o agendador só coleta e grava; o dbt não roda.
python app/scheduler.py --com-dbt
python app/scheduler.py --hora 8 --minuto 30 --com-dbt  # horário customizado
python app/scheduler.py --intervalo 2 --com-dbt         # a cada N horas (debug)
```

O dbt só roda quando a Bronze foi gravada com sucesso. Exemplo de log (os números são ilustrativos):

```text
PIPELINE INICIADO
Etapa 1/3: Coletando vagas...
Coletadas: 87 vagas | Descartadas (fora do tema): 214
Fonte Vagas.com: success | Vagas: 41 | Páginas: 20
Fonte InfoJobs: success | Vagas: 30 | Páginas: 10
Fonte Gupy: success | Vagas: 16 | Páginas: 12
Etapa 2/3: Gravando observações na camada Bronze...
Bronze concluída — 87 observação(ões)
Etapa 3/3: Atualizando a tabela legada jobs...
Persistência concluída — Salvas: 54 | Duplicadas: 33 | Erros: 0
PIPELINE CONCLUÍDO
Executando modelos e testes dbt...
```

Os logs ficam em `logs/pipeline.log`, com rotação a cada 5 MB (3 backups).

O payload Bronze guarda os campos retornados pelo contrato do scraper e o HTML
do card capturado, sem normalização de negócio. `run_id` identifica a execução;
`payload_hash` permite comparar alterações entre coletas. A tabela
`bronze.scrape_runs` também registra fontes vazias ou com falha, permitindo
acompanhar a última execução e verificar freshness mesmo quando não há vagas.

### 5. Camadas dbt

```bash
python app/run_dbt.py debug              # verifica a conexão
python app/run_dbt.py build              # modelos e testes (padrão, sem argumentos)
python app/run_dbt.py source freshness   # alerta em 24 h e erro em 72 h sem coleta
```

O `app/run_dbt.py` lê o `.env` e configura a conexão a partir de `DATABASE_URL`
ou das variáveis `DB_*`. O perfil sem segredos é copiado de
`dbt/profiles.yml.example` para o arquivo local ignorado `dbt/profiles.yml`. O
`build` cria os schemas `silver` e `gold`, então o usuário do PostgreSQL precisa
ter permissão para criar schemas e tabelas. As fontes são declaradas em
`dbt/models/sources.yml`.

| Camada | Modelos | Materialização |
| --- | --- | --- |
| Staging (`silver`) | `stg_vagas_com_jobs`, `stg_infojobs_jobs`, `stg_gupy_jobs`: extraem os campos do payload Bronze, inclusive os novos | view |
| Silver (`silver`) | `jobs`: uma vaga por portal e identificador, com `NULL`, normalização e deduplicação | tabela |
| Gold (`gold`) | `mart_vagas`, `mart_vagas_por_dia`, `mart_vagas_por_origem_localidade`, `mart_demanda_tecnologias`, `mart_status_fontes` | tabela |

Além dos testes declarados nos `.yml` (não nulo, único, valores aceitos), há três
testes em `dbt/tests/` que protegem a Silver: sem ID repetido no mesmo portal,
sem vaga repetida por conteúdo e sem o texto "Não informado" nos campos.

### 6. Exportação para Excel / Power BI

```bash
cd app
python export_excel.py
```

Gera `data/exports/vagas.xlsx` a partir de `gold.mart_vagas`, que alimenta o
dashboard no Power BI. As colunas são `id`, `titulo`, `empresa`, `senioridade`,
`localizacao`, `salario`, `modalidade`, `experiencia`, `escolaridade`,
`qtd_posicoes`, `origem`, `id_externo`, `link`, `descricao`, `data_publicacao`,
`data_coleta` e `tecnologias`. As datas saem no horário de São Paulo, sem fuso.
Execute `python app/main.py` ou `python app/run_dbt.py build` antes de exportar.

---

## Testes

```bash
cd app
pytest tests/ -v
```

Se o `pytest` do venv não for encontrado (acontece quando a pasta do projeto
muda de lugar), use `python -m pytest tests/ -v`.

A suíte usa um mock global do banco (`conftest.py`), então roda sem PostgreSQL. Os testes cobrem scrapers, normalização, salário, analytics, repositórios (inclusive deduplicação por ID e conteúdo e a gravação Bronze), relevância, pipeline, agendamento, exportação, `run_dbt` e configuração. Os parsers do Vagas.com e do InfoJobs também são testados contra **HTML real** dos portais (`app/tests/fixtures/`); quando um portal mudar o layout, salve os cards novos ali e ajuste `test_parsers_html_real.py`. Instale as dependências com `pip install -r requirements.txt` antes de executá-los.

O GitHub Actions roda o `pytest` a cada push e pull request na `main`. O
`dbt build` não roda no CI porque precisa de um PostgreSQL; execute-o localmente
com `python app/run_dbt.py build`.

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

---

## Próximos passos

- Calibrar os seletores do scraper da Gupy e aplicar a ele o filtro de relevância e o contrato de `NULL`
- Buscar a página de detalhe da vaga (descrição completa e salário) nos portais que só mostram um resumo no card
- Adicionar Catho, Remotar e Sólides, e depois LinkedIn, Indeed e Glassdoor
- Migrar o `AnalyticsService` para a Gold e aposentar a tabela `jobs`
- Publicar prints do dashboard do Power BI neste README

---

## Autor

**Willian da Cruz** — projeto de estudo e portfólio em Engenharia de Dados.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-williandacruz-0A66C2?logo=linkedin)](https://www.linkedin.com/in/williandacruz/)
[![GitHub](https://img.shields.io/badge/GitHub-Willian--Cruz-181717?logo=github)](https://github.com/Willian-Cruz)

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).
