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
│   │   ├── salary_service.py
│   │   └── tech_service.py
│   ├── utils/
│   │   └── logger.py
│   ├── generate_dashboard.py
│   └── main.py
│
├── dashboard/
│   └── dashboard.html
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_analytics_service.py
│   ├── test_normalize_service.py
│   └── test_salary_service.py
│
├── .env.example
├── .gitignore
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

### Dashboard

* Chart.js (via CDN)

### Testes

* Pytest

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

```bash
python app/main.py
```

Saída esperada:

```text
Banco criado com sucesso!

VagasScraper: 40 vagas
InfoJobsScraper: 20 vagas

Total coletado: 60 vagas

Salva: Engenheiro de Dados | Senior: Pleno | Local: São Paulo - SP | Salário: Não informado

Processamento finalizado.
```

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

Execute os testes a partir da raiz do projeto:

```bash
pytest tests/ -v
```

Saída esperada:

```text
tests/test_analytics_service.py::TestVagasPorSenioridade::test_retorna_dataframe PASSED
tests/test_analytics_service.py::TestResumoGeral::test_valores_corretos          PASSED
tests/test_normalize_service.py::TestNormalizarSenioridade::test_junior_variantes PASSED
tests/test_normalize_service.py::TestNormalizarLocalizacao::test_remoto           PASSED
tests/test_salary_service.py::TestExtrairSalario::test_faixa_com_rs               PASSED
...
43 passed in 0.52s
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

### ⏳ Sprint 7

* Agendamento automático
* Pipeline diário

### ⏳ Sprint 8

* Deploy em nuvem
* PostgreSQL gerenciado
* Dashboard online

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
![Chart.js](https://img.shields.io/badge/Dashboard-Chart.js-orange)
![Pytest](https://img.shields.io/badge/Testes-Pytest-green)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)

## Estatísticas Atuais

* Vagas coletadas: 60+
* Portais integrados: 2
* Tecnologias monitoradas: 20+
* Testes automatizados: 43
* Banco de dados: PostgreSQL
* Dashboard: HTML estático com Chart.js

---

## 👨‍💻 Autor

Willian

Projeto desenvolvido para fins de estudo, prática de Engenharia de Dados e construção de portfólio profissional.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Willian%20Cruz-blue?logo=linkedin)](https://linkedin.com/in/williandacruz/)
[![GitHub](https://img.shields.io/badge/GitHub-Willian--Cruz-black?logo=github)](https://github.com/Willian-Cruz)

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais informações.