# 🚀 Hub Vagas - Job Market Analytics

Hub Vagas é um projeto de Engenharia de Dados desenvolvido para coletar, armazenar e analisar vagas de emprego da área de Dados e Tecnologia em diferentes portais de recrutamento.

O objetivo é construir uma plataforma capaz de monitorar o mercado de trabalho em tempo real, identificando tendências de contratação, tecnologias mais requisitadas, senioridade, localização e outros indicadores relevantes.

---

## 📌 Objetivos do Projeto

* Coletar vagas de múltiplas plataformas de recrutamento
* Centralizar os dados em um banco PostgreSQL
* Identificar tecnologias mais demandadas pelo mercado
* Mapear distribuição geográfica das vagas
* Analisar senioridade e modelos de trabalho
* Construir dashboards para análise de mercado
* Automatizar todo o pipeline de coleta e atualização

---

## 🏗️ Arquitetura do Projeto

```text
Portais de Vagas
       │
       ▼
    Scrapers
       │
       ▼
 Transformação
 (Normalização + Extração)
       │
       ▼
 PostgreSQL
       │
       ▼
 Dashboards
```

---

## 📂 Estrutura do Projeto

```text
hub_vagas/
│
├── .github/
│   └── workflows/
│       ├── deploy.yml
│       └── dashboard.yml
│
├── app/
│   ├── config/
│   │   └── settings.py
│   ├── constants/
│   │   └── selectors.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   ├── job_model.py
│   │   ├── tech_model.py
│   │   └── job_tech_model.py
│   ├── repositories/
│   │   ├── job_repository.py
│   │   └── tech_repository.py
│   ├── schemas/
│   │   └── job_schema.py
│   ├── scrapers/
│   │   ├── base_scraper.py
│   │   ├── vagas_scraper.py
│   │   └── infojobs_scraper.py
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── collector_service.py
│   │   ├── dashboard_service.py
│   │   ├── job_service.py
│   │   ├── normalize_service.py
│   │   ├── pipeline_service.py
│   │   ├── salary_service.py
│   │   ├── scheduler_service.py
│   │   └── tech_service.py
│   ├── utils/
│   │   └── logger.py
│   ├── generate_dashboard.py
│   ├── main.py
│   └── scheduler.py
│
├── dashboard/
│   └── dashboard.html
│
├── logs/
│   └── pipeline.log
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_analytics_service.py
│   ├── test_normalize_service.py
│   ├── test_pipeline_service.py
│   ├── test_salary_service.py
│   ├── test_scheduler_service.py
│   └── test_scrapers.py
│
├── .env.example
├── .gitignore
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md
```

---

## 🛠️ Tecnologias Utilizadas

### Linguagem

* Python 3.12+

### Banco de Dados

* PostgreSQL
* SQLAlchemy

### Coleta de Dados

* Requests
* BeautifulSoup
* Playwright

### Validação

* Pydantic

### Manipulação de Dados

* Pandas

### Agendamento

* APScheduler

### Dashboard

* Chart.js (via CDN)

### Testes

* Pytest

### CI/CD e Deploy

* GitHub Actions
* Render (Cron Job + PostgreSQL)
* GitHub Pages
* Docker

### Versionamento

* Git
* GitHub

---

## 🌐 Portais Integrados

### Implementados

* ✅ Vagas.com
* ✅ InfoJobs

### Planejados

* ⏳ LinkedIn
* ⏳ Indeed
* ⏳ Glassdoor
* ⏳ Catho
* ⏳ Gupy

---

## 📊 Dados Coletados

Atualmente o sistema coleta e normaliza:

| Campo       | Descrição                              |
| ----------- | -------------------------------------- |
| Título      | Nome da vaga                           |
| Empresa     | Empresa contratante                    |
| Senioridade | Padronizado: Júnior, Pleno, Sênior etc |
| Localização | Padronizado: Cidade - UF / Remoto      |
| Salário     | Extraído da descrição quando disponível|
| Descrição   | Resumo da vaga                         |
| Link        | URL da vaga                            |
| Origem      | Portal de recrutamento                 |

---

## 🧠 Tecnologias Identificadas

O projeto realiza extração automática de tecnologias mencionadas nas descrições das vagas.

Exemplos:

* Python
* SQL
* Power BI
* Tableau
* Spark
* Databricks
* AWS
* Azure
* GCP
* Airflow
* Kafka
* Docker
* Kubernetes

---

## ⚙️ Instalação

Clone o repositório:

```bash
git clone https://github.com/Willian-Cruz/hub_vagas.git
```

Entre na pasta:

```bash
cd hub_vagas
```

Crie o ambiente virtual:

```bash
python -m venv venv
```

Ative o ambiente:

Windows

```bash
venv\Scripts\activate
```

Linux/Mac

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuração

Crie um arquivo `.env` baseado no `.env.example`:

```env
DB_USER=usuario
DB_PASSWORD=senha
DB_HOST=localhost
DB_PORT=5432
DB_NAME=job_market
```

---

## ▶️ Executando o Projeto

### Execução manual (uma vez)

```bash
python app/main.py
```

### Agendamento automático (pipeline diário)

```bash
# Todo dia às 06:00 — horário de São Paulo (padrão)
python app/scheduler.py

# Horário customizado
python app/scheduler.py --hora 8 --minuto 30

# Modo debug — a cada N horas
python app/scheduler.py --intervalo 2
```

Saída esperada no terminal:

```text
2026-01-15 06:00:00 | INFO     | services.pipeline_service | PIPELINE INICIADO
2026-01-15 06:00:00 | INFO     | services.pipeline_service | Etapa 1/3: Coletando vagas...
2026-01-15 06:04:21 | INFO     | services.pipeline_service | Coletadas: 87 vagas
2026-01-15 06:04:21 | INFO     | services.pipeline_service | Etapa 2/3: Persistindo no banco...
2026-01-15 06:04:23 | INFO     | services.pipeline_service | Persistência concluída — Salvas: 54 | Duplicadas: 33 | Erros: 0
2026-01-15 06:04:23 | INFO     | services.pipeline_service | Etapa 3/3: Regenerando dashboard...
2026-01-15 06:04:24 | INFO     | services.pipeline_service | PIPELINE CONCLUÍDO em 264.3s
```

Os logs são gravados em `logs/pipeline.log` com rotação automática a cada 5 MB.

---

## 📊 Gerando o Dashboard

Com o banco populado, rode:

```bash
python app/generate_dashboard.py
```

Isso gera o arquivo `dashboard/dashboard.html`. Abra-o direto no navegador — sem servidor necessário.

O dashboard exibe:

* KPIs gerais: total de vagas, empresas, tecnologias e portais
* Vagas por senioridade
* Modalidade de trabalho (Remoto, Híbrido, Presencial)
* Top 15 tecnologias mais demandadas
* Top 10 localizações
* Vagas por portal de origem
* Transparência salarial

---

## 🧪 Testes

Execute os testes a partir da pasta `app/`:

```bash
cd app
pytest tests/ -v
```

Saída esperada:

```text
tests/test_analytics_service.py   PASSED  (23 testes)
tests/test_normalize_service.py   PASSED  (10 testes)
tests/test_pipeline_service.py    PASSED  (14 testes)
tests/test_salary_service.py      PASSED  ( 7 testes)
tests/test_scheduler_service.py   PASSED  (15 testes)
tests/test_scrapers.py            PASSED  (18 testes)
tests/test_settings.py            PASSED  ( 5 testes)
tests/test_normalize_service.py   PASSED  ( 3 testes)
...
95 passed in 5.66s
```

---

## 📈 Sprints

### ✅ Sprint 1 — Estrutura inicial

* Conexão com PostgreSQL
* Estrutura de pastas e arquivos
* Modelo de dados base

### ✅ Sprint 2 — Persistência

* Gravação de vagas no banco
* Validação com Pydantic

### ✅ Sprint 3 — Scrapers

* Scraper Vagas.com
* Scraper InfoJobs
* Coleta simultânea via CollectorService

### ✅ Sprint 4 — Tecnologias

* Extração automática de tecnologias nas descrições
* Tabela `technologies` e relação many-to-many com `jobs`

### ✅ Sprint 5 — Normalização e Salários

* Normalização de senioridade (Júnior, Pleno, Sênior, Estágio etc.)
* Normalização de localização (Cidade - UF, Remoto, Híbrido)
* Extração de salários via regex na descrição
* Testes unitários com Pytest (20 testes)

### ✅ Sprint 6 — Dashboard Analítico

* `AnalyticsService`: 6 consultas SQL retornando DataFrames (senioridade, localização, modalidade, tecnologias, origem, salários)
* `DashboardService`: geração de HTML estático com Chart.js
* KPIs no cabeçalho: vagas, empresas, tecnologias, portais
* `conftest.py`: mock global do banco para testes sem PostgreSQL
* Testes unitários com mock (23 testes, total acumulado: 43)

### ✅ Sprint 7 — Agendamento e Pipeline

* `PipelineService`: orquestra coleta → persistência → dashboard em uma execução única, retornando métricas (coletadas, salvas, duplicadas, erros, duração)
* `SchedulerService`: agendamento com APScheduler — modo diário (cron) e modo intervalo, timezone America/Sao_Paulo
* `scheduler.py`: ponto de entrada com CLI (`--hora`, `--minuto`, `--intervalo`)
* `logger.py`: logging estruturado com `RotatingFileHandler` (5 MB, 3 backups), gravado em `logs/pipeline.log`
* `conftest.py` atualizado: mock global de `database.connection` e `database.models`
* Testes unitários (15 testes, total acumulado: 90)

### ✅ Sprint 8 — Deploy em Nuvem

* `Dockerfile`: container Python 3.12 com Chromium para o Playwright
* `render.yaml`: Infrastructure as Code — banco PostgreSQL + Cron Job no Render
* `.github/workflows/deploy.yml`: CI/CD automático — testa (95 testes) e aciona deploy via API do Render a cada push na main
* `.github/workflows/dashboard.yml`: publica `dashboard.html` no GitHub Pages automaticamente
* Deploy: Render (Cron Job `0 9 * * *` = 06:00 Brasília) + PostgreSQL gerenciado
* Dashboard público: `https://willian-cruz.github.io/hub_vagas/`
* Testes de settings (5 testes, total acumulado: 95)

---

## 🎯 Casos de Uso

* Estudo do mercado de trabalho em Dados
* Planejamento de carreira
* Identificação de tecnologias em alta
* Construção de portfólio de Engenharia de Dados
* Monitoramento de tendências de contratação

---

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED?logo=docker)
![Render](https://img.shields.io/badge/Render-Cron%20Job-46E3B7)
![APScheduler](https://img.shields.io/badge/Agendamento-APScheduler-blueviolet)
![Chart.js](https://img.shields.io/badge/Dashboard-Chart.js-orange)
![Pytest](https://img.shields.io/badge/Testes-95%20passed-green)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions)
![Status](https://img.shields.io/badge/Status-Em%20Produção-brightgreen)

## Estatísticas Atuais

* Vagas coletadas: 100+
* Portais integrados: 2
* Tecnologias monitoradas: 20+
* Testes automatizados: 95
* Banco de dados: PostgreSQL (Render)
* Dashboard: https://willian-cruz.github.io/hub_vagas/
* Agendamento: Render Cron Job (diário às 06:00, Brasília)
* CI/CD: GitHub Actions (deploy automático a cada push)

---

## 👨‍💻 Autor

Willian

Projeto desenvolvido para fins de estudo, prática de Engenharia de Dados e construção de portfólio profissional.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Willian%20Cruz-blue?logo=linkedin)](https://linkedin.com/in/williandacruz/)
[![GitHub](https://img.shields.io/badge/GitHub-Willian--Cruz-black?logo=github)](https://github.com/Willian-Cruz)

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais informações.