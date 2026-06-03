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
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── scrapers/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── data/
├── logs/
├── tests/
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

Atualmente o sistema coleta:

| Campo       | Descrição                 |
| ----------- | ------------------------- |
| Título      | Nome da vaga              |
| Empresa     | Empresa contratante       |
| Senioridade | Júnior, Pleno, Sênior etc |
| Localização | Cidade/Estado             |
| Descrição   | Resumo da vaga            |
| Link        | URL da vaga               |
| Origem      | Portal de recrutamento    |

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
DATABASE_URL=postgresql://usuario:senha@localhost:5432/job_market
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

Processamento finalizado.
```

---

## 📈 Próximos Passos

### Sprint 5

* Normalização de senioridade
* Normalização de localização
* Extração de salários

### Sprint 6

* Dashboard analítico
* Indicadores de mercado

### Sprint 7

* Agendamento automático
* Pipeline diário

### Sprint 8

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
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-green)

## Estatísticas Atuais

- Vagas coletadas: 60+
- Portais integrados: 2
- Tecnologias monitoradas: 20+
- Banco de dados: PostgreSQL

## 👨‍💻 Autor

Willian

Projeto desenvolvido para fins de estudo, prática de Engenharia de Dados e construção de portfólio profissional.

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais informações.
