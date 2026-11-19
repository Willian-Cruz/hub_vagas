# Checklist de Melhorias — hub_vagas

Este documento rastreia o progresso das 20 melhorias identificadas na análise crítica. Atualizado a cada item concluído.

**Legenda de status:**
- `pendente` — não iniciado
- `em andamento` — em execução
- `feito` — concluído, testes verdes, documentado
- `bloqueado` — depende de algo externo (humano, acesso a portal, etc.)
- `pendente(humano)` — aguarda ação do dono do projeto

**Data de início:** 2026-11-19

---

## Fase 0 — Preparação

| Item | Título | Fase | Status | Data | Evidência (commit/teste) | Subtarefas pendentes |
|------|--------|------|--------|------|--------------------------|----------------------|
| 0 | Preparação (baseline, inventário, checklist, AGENTS.md) | 0 | **em andamento** | 2026-11-19 | — | Baseline: unit 323 passed, 34 deselected; integration 9 failed, 19 passed (dbt build falhou, alguns testes de migration). Inventário: `seniority_service.py` e `test_seniority_service.py` citados no MAPA mas não existem no fonte; `dashboard_service.py` e `infojobs_parser.py` só como .pyc. Fixtures `catho_cards_2026_11.html` e `infojobs_cards_2026_11.html` existem. |

---

## Fase 1 — Rede de segurança, integridade e documentação

| Item | Título | Fase | Status | Data | Evidência | Subtarefas pendentes |
|------|--------|------|--------|------|-----------|----------------------|
| 18 | Higiene do repositório e segurança | 1 | `pendente` | — | — | `git rm` de HTML gigante e .pyc; completar .gitignore; limpar .env.example; pre-commit hooks; teste de fixtures sensíveis; auditoria histórico; CONTRIBUTING.md |
| 6a | Rede de segurança de integração (antes dos itens 1 e 2) | 1 | `pendente` | — | — | Marcador `integration` e fixture com `HUB_VAGAS_TEST_DATABASE_URL`; teste offline ponta a ponta; `unit_tests:` do dbt para senioridade/modalidade/salário; CI com service container postgres |
| 1 | Bronze fiel: nunca alterar o HTML antes de gravar | 1 | `pendente` | — | — | Auditar scrapers/parsers por mutação de card; corrigir capturando str(card) antes; teste parametrizado para todos |
| 2 | Senioridade: corrigir e ter uma única fonte da regra | 1 | `pendente` | — | — | Corrigir macro e NormalizeService (PL/SQL, Liderança); seed `seniority_rules.csv` como fonte única; preservar comportamento documentado; teste paridade Python↔SQL; `unit_tests:` dbt |
| 4 | Documentação sincronizada com o estado real | 1 | `pendente` | — | — | ADRs para decisões do RESUMO; `docs/runbook.md` esqueleto; `CHANGELOG.md`; README corrigido (número de testes, mapa de código); mover pendências para checklist; `git mv` RESUMO/MAPA para `docs/contexto/` |
| 20 | Backlog unificado com critérios de aceite | 1 | `pendente` | — | — | Criar `docs/BACKLOG.md` unificando RESUMO §14 + MAPA + itens desta lista; critério de aceite mensurável por item; política LinkedIn/Indeed/Glassdoor só via API |

---

## Fase 2 — Schema versionado e qualidade de dados

| Item | Título | Fase | Status | Data | Evidência | Subtarefas pendentes |
|------|--------|------|--------|------|-----------|----------------------|
| 8 | Migrações versionadas com Alembic | 2 | `pendente` | — | — | Adicionar Alembic, alembic.ini, pasta revisões; env.py com resolução de conexão; revisão baseline manual; teste `alembic upgrade head` + `alembic check`; documentar `alembic stamp` para bancos existentes; script `verificar_estado_banco.py`; trocar `create_all()` por `alembic upgrade head` em main.py; mover SQLs legados para `infra/migrations_legado/` |
| 3 | Qualidade dos campos e freshness | 2 | `pendente` | — | — | Colunas `descartadas` e parâmetros da consulta em `bronze.scrape_runs` via Alembic; seed `data_quality_thresholds.csv` e modelo `gold.mart_qualidade_campos`; freshness em `sources.yml` com filter; teste singular de recência em `mart_vagas`; InfoJobs: WARNING para chip desconhecido |
| 5 | Relevância decidida na Silver (Bronze guarda tudo) | 2 | `pendente` | — | — | Scrapers devolvem todas as vagas (`discarded`=0); config `RELEVANCE_MODE`; mover `TERMOS_TITULO` para seed `relevance_terms.csv`; modelo intermediário calcula `relevante` + `termo_casado`; Gold/Excel filtram `relevante=true`; tabela legada `jobs` continua só relevantes; `gold.mart_status_fontes` com descartadas; script `avaliar_relevancia.py`; testes |

---

## Fase 3 — Coleta responsável e operação

| Item | Título | Fase | Status | Data | Evidência | Subtarefas pendentes |
|------|--------|------|--------|------|-----------|----------------------|
| 10 | Coleta responsável e robusta | 3 | `pendente` | — | — | `HttpClient` compartilhado (timeouts, retry, backoff, jitter, `Retry-After`, intervalo mínimo, User-Agent configurável, TLS validado); scrapers instanciáveis com cliente injetado; Playwright centralizado; `docs/portais.md` com seção por portal (robots.txt, termos, endpoint, limite, data checagem = A VERIFICAR PELO HUMANO); testes com responses/requests-mock |
| 9 | Orquestração confiável e observável | 3 | `pendente` | — | — | `scheduler.py`: dbt ligado por padrão (`--sem-dbt` para desligar); APScheduler `coalesce=True`, `max_instances=1`, `misfire_grace_time`; trava única via `pg_try_advisory_lock`; status `success/degraded/failed` com códigos 0/2/1; notificação opcional (webhook/SMTP) em degraded/failed/freshness; completar `docs/runbook.md` (sintoma→verificação→ação); documentar alternativas schtasks/GitHub Actions cron |
| 6b | Canário de layout (depende do item 10) | 3 | `pendente` | — | — | `scripts/canario_portais.py` (usa HttpClient/Playwright); `.github/workflows/canary.yml` semanal + dispatch, não bloqueante; testar lógica offline com fixtures; `TODO(humano)` para primeira execução |
| 11 | Reprodutibilidade | 3 | `pendente` | — | — | `docker-compose.yml` com postgres:16; `pyproject.toml` com extras `dev`; fixar `dbt-core`/`dbt-postgres`; lockfile (`uv.lock` ou `pip-compile`); `requirements.txt` gerado; caminhos ancorados via `settings`; `Makefile` + `tasks.ps1` com mesmos alvos; README Windows + Linux/macOS; NÃO reorganizar pastas |

---

## Fase 4 — Modelo analítico

| Item | Título | Fase | Status | Data | Evidência | Subtarefas pendentes |
|------|--------|------|--------|------|-----------|----------------------|
| 14 | Deduplicação e grão | 4 | `pendente` | — | — | Eliminar por conteúdo só sem `id_externo`; com ID, unicidade `(origem, id_externo)`; `qtd_anuncios_mesma_chave`; `vaga_canonica_id` (hash empresa+título+cidade); `qtd_portais`; `dbt/analyses/amostra_duplicatas_cross_portal.sql`; documentar contagens como "anúncios"; acrescentar `vagas_unicas_estimadas` e `posicoes_totais` ao mart diário |
| 13 | Salário estruturado | 4 | `pendente` | — | — | Silver/mart: `salario_min`, `salario_max` (numeric), `salario_periodo`, `salario_tipo`, `moeda` (BRL), `salario_fonte`, `salario_texto` (original); NULL quando sem valor; "A combinar" → tipo `a_combinar` com min/max NULL; macro `parse_salary` no dbt; `gold.mart_salario_por_senioridade` (mediana, n_com_salario, pct_com_salario); aviso de viés na descrição |
| 12 | Ciclo de vida da vaga | 4 | `pendente` | — | — | Modelo incremental (`unique_key`) grão `(origem, coalesce(id_externo, source_job_id))`: `first_seen_at`, `last_seen_at`, `n_observacoes`, `dias_visivel`, `visivel_na_ultima_coleta_ok`; só avaliar "sumiu" contra última execução `success`; `gold.mart_tempo_aberta` (mediana dias_visivel por origem, senioridade, semana); testes com 3 execuções simuladas |
| 16 | Taxonomia de senioridade: nível × trilha (depende itens 2 e 5) | 4 | `pendente` | — | — | Silver: `nivel`, `trilha`, `senioridade_origem`, `senioridade_confianca`; manter `senioridade` inalterada; sinais brutos até a Silver; ADR com mapeamento rótulos atuais → nível×trilha |
| 15 | Dimensão geográfica | 4 | `pendente` | — | — | Seed `municipios_ibge.csv` (script `gerar_seed_municipios.py` baixa do IBGE — `TODO(humano)` se sem internet); `silver.dim_localidade`; resolver `uf`/`regiao` em `mart_vagas`: "Cidade - UF" direto; só cidade se único, senão `uf` NULL + `localidade_ambigua=true`; "Todo Brasil" → `abrangencia='nacional'` + `localizacao` NULL; InfoJobs: extrair `data-vagalatitude/longitude` do `source_payload`; `gold.mart_vagas_por_uf` |
| 17 | Camada de consumo e documentação de dados | 4 | `pendente` | — | — | Descrição de todos modelos/colunas nos YAML (grão explícito); `dbt docs generate` no CI com artefato; `exposures` para dashboard (`url` = TODO(humano)); exportação como último passo do `main.py` (`--sem-export`); `docs/power_bi.md` (conectar à Gold, colunas, medidas); `docs/img/` placeholders prints; `docs/convencoes.md` (Bronze/Silver inglês técnico, Gold português negócio, só objetos novos) |

---

## Fase 5 — Simplificação e extensibilidade

| Item | Título | Fase | Status | Data | Evidência | Subtarefas pendentes |
|------|--------|------|--------|------|-----------|----------------------|
| 7 | Preparar aposentadoria da `jobs` legada (sem remover nada) | 5 | `pendente` | — | — | `scripts/reconciliar_legado_silver.py` (compara `jobs` × `silver.jobs`, grava CSV, exit code ≠ 0 se divergência > limite); migrar `AnalyticsService` para Gold mantendo interface; etapa 3 opcional por `ENABLE_LEGACY_JOBS` (default ligado); teste paridade 18 tecnologias `tech_service` vs macro `monitored_technologies`; ADR com critério de saída (14 dias sem divergência) e lista exata do que remover; NÃO apagar nada nesta rodada |
| 19 | Reduzir acoplamento para novos portais | 5 | `pendente` | — | — | Seed `portais.csv` ou `var` dbt alimenta testes `accepted_values` e `union all` via macro; padrão "buscador + parser puro" para Vagas.com e InfoJobs (como `catho_parser`); `scripts/capturar_amostra.py <portal>` (salva só cards, sanitizado, em `app/tests/fixtures/` com data; não executar — testar só sanitização); atualizar README "Como adicionar um novo portal" (alvo: 1 scraper + 1 linha seed + fixtures + testes) |