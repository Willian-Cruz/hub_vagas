# Histórico de Desenvolvimento — Hub Vagas

Cronologia das principais etapas de evolução do projeto.

---

| Etapa | Período | Entregas |
|-------|---------|----------|
| 1 a 2 | — | Estrutura, conexão com PostgreSQL, persistência e validação com Pydantic |
| 3 | — | Scrapers do Vagas.com e InfoJobs, coleta consolidada no CollectorService |
| 4 | — | Extração de tecnologias e relação many-to-many `jobs` ↔ `technologies` |
| 5 | — | Normalização de senioridade e localização, extração de salário |
| 6 a 7 | — | AnalyticsService, PipelineService com métricas, APScheduler e logging estruturado |
| 8 | jun/2026 | Deploy em Render (Cron Job + PostgreSQL), Docker e dashboard HTML no GitHub Pages |
| 9 | jun/2026 | Deploy em nuvem e dashboard HTML descontinuados; análise migrada para Excel + Power BI |
| 10 | out/2026 | Correções de métricas do pipeline, código de saída do `main.py` e testes do repositório |
| 11 | — | Camadas Bronze, Silver e Gold: coleta append-only em JSONB, transformações e testes de dados com dbt, exportação a partir do mart Gold e tabela `jobs` mantida como legado |
| 12 | nov/2026 | Revisão dos scrapers do Vagas.com e InfoJobs com HTML real: campos vazios viram `NULL`, novos campos, filtro de relevância, deduplicação por ID e conteúdo (migração `004`) |
| 13 | nov/2026 | Senioridade em cascata (portal, título, descrição e experiência), parser da Catho com HTML real, correções no InfoJobs: modalidade pelos três ícones do card |
| 14 | nov/2026 | Arquitetura medallion com `raw.job_observations` como raw; `bronze.scrape_runs` como metadado de execução; `scheduler.py` desacoplado do dbt |
| 15 | nov/2026 | Coleta e parser da Catho com HTML real, staging `stg_catho_jobs` no dbt, scripts de verificação de qualidade, ajustes na macro `classify_seniority_cascade` |
| 16 | nov/2026 | Fase 1 — Dados: `dias_no_ar` / `is_ativa` na Silver; métricas novas vs revistas; salário estruturado (`salario_texto`/`min`/`max`/`tipo`, sem "A combinar" como fallback); `mart_salarios` com mediana/média por senioridade+origem; senioridade única no dbt (PL/SQL e PL-300 não são Pleno; "Liderança" reconhecida); 25 termos de tecnologias na seed; dedup por portal documentado; ADRs 0001 e 0002 |
| 17 | nov/2026 | Fase 2 — Qualidade automática: source freshness com `filter` em `bronze.scrape_runs`; limiares em `vars:` do `dbt_project.yml`; testes de desvio de qualidade vs mediana 7d e volume vs média semanal; `check_*.py` removidos da raiz (lógica em testes dbt); `data_publicacao` como `timestamptz` (UTC); `data_atualizacao` para Catho; teste de contrato Python↔dbt |
| 18 | nov/2026 | Fase 3 — Operação, CI, segurança e compliance: Windows Task Scheduler (XML + PowerShell); notificação de falha (webhook/e-mail); retry com backoff; advisory lock; `schema_migrations` + `migrate.py`; role `bi_reader` + `+grants` no dbt; `docs/compliance.md`; CI com `services: postgres`, pytest integration, ruff, pre-commit, pip-tools lock (`requirements.in`) |
| 19 | nov/2026 | Fase 4 — Refinamentos: `detail_url` no `JobSchema`; `fetch_detail_page` / `_merge_detail_into_vaga` no `BaseScraper`; deep scraping para Vagas.com (descrição completa + salário); guia de expansão para portais (Remotar, Sólides, LinkedIn, Indeed, Glassdoor); `AnalyticsService` auditado e funcional (consulta Gold); `.env.example` limpo (sem Cloud Run/Cloud SQL/DASHBOARD_URL); `ARCHITECTURE.md` consolidado no README |
| 20 | nov/2026 | Fase 2 — Arquitetura e organização: `ARCHITECTURE.md` com diagrama real de fluxo de dados; camadas Medallion com responsabilidades claras; `docs/data_dictionary/data_dictionary.md`; `docs/operations/troubleshooting.md`; `docs/history/development_history.md`; campos de linhagem (M09): `ingested_at`, `scraper_version`, `run_id` na raw e Silver; flags de inferência (`senioridade_inferida`, `salario_inferido`); `pyproject.toml` como pacote instalável com entry points CLI; `app/__init__.py`; `CONTRIBUTING.md` e `CHANGELOG.md` |
