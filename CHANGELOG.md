# Changelog — Hub Vagas

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adota versionamento semântico ([SemVer](https://semver.org/)).

---

## [1.0.0] — 2026-11-18

### Adicionado
- Arquitetura medallion com `raw.job_observations` como camada Raw (append-only, JSONB).
- `bronze.scrape_runs` como metadado operacional de execução (não camada de negócio).
- `silver.jobs` com normalização, dedup cross-portal, `dias_no_ar`, `is_ativa`.
- 7 marts Gold: `mart_vagas`, `mart_vagas_por_dia`, `mart_vagas_por_origem_localidade`,
  `mart_demanda_tecnologias`, `mart_status_fontes`, `mart_salarios`, `mart_qualidade_campos`.
- Filtro de relevância Opção A: `is_relevant` / `motivo_relevancia` gravados na raw, Silver filtra.
- Salário estruturado: `salario_texto`, `salario_min`, `salario_max`, `salario_tipo` (faixa/exato/a_combinar/nao_informado).
- "A combinar" não é mais fallback da descrição.
- Senioridade única no dbt (`normalize_seniority` + `classify_seniority_cascade`).
- PL/SQL, PL-SQL, PL SQL, PL-300 não são mapeados como Pleno.
- Rótulo "Liderança" reconhecido como entrada de senioridade.
- 25 termos de tecnologias monitoradas na seed `tecnologias_monitoradas.csv`.
- Dedup por portal documentado (mesma vaga em 2 portais conta 2×).
- Deep scraping para Vagas.com (`detail_url`, `fetch_detail_page`, `MAX_DETAIL_PAGES=5`).
- `scraper_version` gravada em `raw.job_observations` para linhagem de dados.
- `ingested_at` gravado em `raw.job_observations` (momento da persistência).
- `run_id`, `scraper_version`, `ingested_at` propagados da raw para a Silver.
- Flags de inferência: `senioridade_inferida`, `salario_inferido`.
- Agendador de Tarefas Windows (`scripts/task_hub_vagas_coletadiaria.xml` + PowerShell).
- Notificação de falha via webhook/e-mail (`notifier.py`).
- Retry com backoff exponencial + jitter nos scrapers (`BaseScraper.coletar_com_retry`).
- Trava contra execução simultânea (`pg_try_advisory_lock`, mesma conexão).
- Role `bi_reader` (migração 008) + `+grants select: ['bi_reader']` no dbt.
- Tabela `schema_migrations` (migração 007) com detecção de modificação não permitida (migração 009).
- CI: pytest com `services: postgres`, dbt build, ruff, pip-tools lock, detect-secrets.
- pyproject.toml como pacote instalável (`pip install -e .`).
- Entry points CLI: `hub-vagas-ingest`, `hub-vagas-transform`, `hub-vagas-scheduler`.
- ADRs: `docs/adr/0001-jobs-como-raw.md`, `docs/adr/0002-filtro-de-relevancia.md`.
- `docs/compliance.md` com conformidade por portal (robots.txt, termos, rate limit).
- `ARCHITECTURE.md` com diagrama real do fluxo de dados.

### Alterado
- `.env` removido do rastreamento Git (credenciais reais estavam expostas).
- `.gitignore` agora bloqueia `.env`, `.env.*`, `*.pem`, `*.key`, `credentials.json`, `secrets/`.
- `pyproject.toml`: adicionado `[build-system]`, `[tool.setuptools.packages.find]`, `[project.scripts]`.
- `app/__init__.py` criado para torná-lo um pacote Python instalável.
- `data_publicacao` como `timestamptz` (UTC) em todos os staging models.
- `data_atualizacao` adicionada aos staging models (apenas Catho preenche).
- `data_publicacao_precisao` (hora/dia/estimada) na Silver.
- `app/services/seniority_service.py` removido (senioridade agora é única no dbt).
- `app/services/normalize_service.py`: `normalizar_senioridade` removido.
- Seis scripts `check_*.py` removidos da raiz (lógica convertida em testes dbt).
- README reescrito como fonte única de verdade da documentação.

### Corrigido
- INSERT em `raw.job_observations` estava quebrado (sintaxe de parâmetros + cast `::jsonb`).
- `json.dumps` sem `default=str` causava `TypeError` em payloads com `datetime`.
- Advisory lock era adquirido e liberado em conexões diferentes (não protegia a execução).
- Teste dbt `assert_silver_jobs_unique_by_content` contradizia o design de dedup.
- `analytics_service.py` referenciava tabela `technologies` inexistente (agora usa `gold.mart_demanda_tecnologias`).
- `macro salario_min/salario_max` usavam sintaxe inválida de `replace()` com 4 argumentos.

### Removido
- `ARCHITECTURE.md` (conteúdo consolidado no novo `ARCHITECTURE.md` na raiz e no README).
- `app/services/seniority_service.py`
- `check_catho.py`, `check_data_quality.py`, `check_gold_tech.py`, `check_nulls.py`, `check_silver_catho.py`, `check_values.py`

---

## [0.x.x] — Versões anteriores

Versões anteriores não mantiveram este changelog. Consulte o histórico do Git
para mudanças antes da versão 1.0.0.
