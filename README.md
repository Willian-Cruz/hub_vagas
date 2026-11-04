# Hub Vagas — Job Market Analytics

[![CI Hub Vagas](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml/badge.svg)](https://github.com/Willian-Cruz/hub_vagas/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQLAlchemy-336791?logo=postgresql&logoColor=white)
![Playwright](https://img.shields.io/badge/Coleta-Playwright-2EAD33?logo=playwright&logoColor=white)
![Power BI](https://img.shields.io/badge/Dashboard-Power%20BI-F2C811?logo=powerbi&logoColor=black)
![License](https://img.shields.io/badge/licen%C3%A7a-MIT-lightgrey)

Pipeline ETL em Python que coleta vagas de Dados e Tecnologia em portais brasileiros, normaliza os campos, extrai as tecnologias citadas e grava tudo em PostgreSQL. Os dados tratados são exportados para Excel e analisados em um dashboard no Power BI.

A execução é em **lote (batch)**: uma vez por dia via APScheduler, ou manualmente.

---

## Arquitetura

```mermaid
flowchart LR
    A[Portais de vagas<br/>Vagas.com · InfoJobs · Gupy] --> B[Scrapers<br/>Playwright + BeautifulSoup]
    B --> C[Validação<br/>Pydantic]
    C --> D[Normalização<br/>senioridade · local · salário · tecnologias]
    D --> E[(PostgreSQL)]
    E --> F[Exportação<br/>Excel .xlsx]
    F --> G[Dashboard<br/>Power BI]
```

| Etapa | Onde fica | O que faz |
| --- | --- | --- |
| Coleta | `app/scrapers/`, `app/services/collector_service.py` | Roda cada scraper em sequência; a falha de um não interrompe os outros |
| Relevância | `app/services/relevance_service.py` | Descarta, ainda no scraper, vagas cujo **título** não é da área de dados; a contagem de descartadas vai para o log e as métricas |
| Validação | `app/schemas/job_schema.py` | Garante o formato de cada vaga com Pydantic |
| Normalização | `app/services/normalize_service.py`, `salary_service.py`, `tech_service.py` | Padroniza senioridade e localização, extrai salário via regex e identifica tecnologias |
| Persistência | `app/repositories/` | Grava em PostgreSQL. Duplicada = mesmo link, **ou** mesmo ID no portal (`origem` + `id_externo`), **ou** mesmo conteúdo (`origem` + título + empresa + local, sem acento/caixa). Ao reencontrar uma vaga, só preenche campos que estavam `NULL`; nunca sobrescreve |
| Orquestração | `app/services/pipeline_service.py`, `app/scheduler.py` | Executa coleta + persistência e registra métricas (coletadas, salvas, duplicadas, erros, duração) |
| Exportação | `app/services/export_service.py`, `app/export_excel.py` | Gera `data/exports/vagas.xlsx` com as tecnologias agregadas por vaga |

## Modelo de dados

```mermaid
erDiagram
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
│   ├── database/              # conexão e modelos SQLAlchemy (jobs, technologies, job_technologies)
│   ├── repositories/          # gravação no banco (job_repository, tech_repository)
│   ├── schemas/job_schema.py  # validação Pydantic
│   ├── scrapers/              # base_scraper, vagas_scraper, infojobs_scraper, gupy_scraper
│   ├── services/              # analytics, collector, export, job, normalize, pipeline,
│   │                          # relevance, salary, scheduler, tech
│   ├── tests/                 # testes + conftest.py (banco mockado) + fixtures/ (HTML real dos portais)
│   ├── utils/                 # logger (rotação de arquivo), text_utils, date_utils
│   ├── debug_vagas.py         # diagnóstico visual do scraper do Vagas.com
│   ├── export_excel.py        # ponto de entrada da exportação
│   ├── main.py                # execução única do pipeline
│   └── scheduler.py           # execução agendada
├── infra/migrations/          # SQL para bancos criados por versões anteriores (001 a 003)
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
esse timestamp.

A migração `003` (idempotente) adiciona `id_externo`, `data_publicacao`,
`modalidade`, `experiencia`, `escolaridade`, `qtd_posicoes` e `chave_conteudo`;
preenche `id_externo` a partir dos links já gravados; troca os textos
"Não informado", "Confidencial" e "Localização Não Informada" por `NULL`; e cria
o índice único `(origem, id_externo)`. Ela **interrompe** se houver ID repetido
no mesmo portal. Faça um `pg_dump` antes de aplicar:

```bash
pg_dump "$DATABASE_URL" > backup_antes_da_003.sql
psql "$DATABASE_URL" -f infra/migrations/003_jobs_novos_campos.sql
```

Campo sem informação é `NULL`, nunca o texto "Não informado". No Power BI, trate
`NULL` como "(Em branco)". A `data_coleta` de vagas anteriores à migração `002` não
é confiável (todas recebem o horário da migração); use `data_publicacao`.

### 3. Pipeline

```bash
# Execução única (coleta + persistência). Sai com código 1 se falhar
# ou se nenhuma vaga for coletada.
python app/main.py

# Execução agendada: todo dia às 06:00, horário de São Paulo (padrão)
python app/scheduler.py
python app/scheduler.py --hora 8 --minuto 30   # horário customizado
python app/scheduler.py --intervalo 2          # a cada N horas (debug)
```

Exemplo de log:

```text
PIPELINE INICIADO
Etapa 1/2: Coletando vagas...
Coletadas: 87 vagas | Descartadas (fora do tema): 214
Etapa 2/2: Persistindo no banco...
Persistência concluída — Salvas: 54 | Duplicadas: 33 | Erros: 0
PIPELINE CONCLUÍDO
```

Os logs ficam em `logs/pipeline.log`, com rotação a cada 5 MB (3 backups).

### 4. Exportação para Excel / Power BI

```bash
cd app
python export_excel.py
```

Gera `data/exports/vagas.xlsx`, que alimenta o dashboard no Power BI.

---

## Testes

```bash
cd app
pytest tests/ -v
```

A suíte usa um mock global do banco (`conftest.py`), então roda sem PostgreSQL. Os testes cobrem scrapers, normalização, salário, analytics, repositórios (inclusive deduplicação por ID e por conteúdo), relevância, pipeline, agendamento, exportação e configuração. Os parsers do Vagas.com e do InfoJobs também são testados contra **HTML real** dos portais (`app/tests/fixtures/`); quando um portal mudar o layout, salve os cards novos ali e ajuste os testes de `test_parsers_html_real.py`. Instale as dependências com `pip install -r requirements.txt` antes de executá-los. O GitHub Actions roda a suíte a cada push e pull request na `main`.

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
| 11 (nov/2026) | Revisão dos scrapers do Vagas.com e InfoJobs com HTML real: campos vazios viram `NULL`, novos campos, filtro de relevância, deduplicação por ID e conteúdo, migração `003` |

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

