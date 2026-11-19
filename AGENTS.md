# AGENTS.md — Comandos e Regras do Projeto hub_vagas

Este arquivo resume as regras de trabalho (Seção 2 do prompt principal) e os comandos de teste, lint e dbt para Windows (PowerShell) e Linux/macOS (bash).

---

## Regras Obrigatórias (Resumo)

1. **Git:** Nunca commite na `main`. Uma branch por fase (`melhorias/fase-N-<tema>`), commits pequenos e atômicos, um PR por item ou grupo coeso. Nunca `push --force` nem reescreva histórico.
2. **Base correta:** Confirme que a base contém Bronze/dbt (`dbt/` e `app/database/bronze_model.py`). Se `main` não contiver, parta da branch `ajustes-bronze-dbt` e registre no relatório.
3. **Testes:** Todo comportamento alterado ganha teste (bug corrigido = teste de regressão). Rode `python -m pytest tests/` dentro de `app/`. Nunca remova nem enfraqueça teste para passar; se errado, explique e corrija com justificativa.
4. **Sem PostgreSQL?** Suba temporário (initdb em pasta temporária ou serviço local). Se não der, escreva testes de integração com `@pytest.mark.integration` (pulados sem `HUB_VAGAS_TEST_DATABASE_URL`), garanta que rodem no CI e diga no relatório o que não pôde executar. Nunca declare "validado" o que não executou.
5. **Sem acesso aos portais:** Não acesse Vagas.com, InfoJobs, Gupy nem outros sites. Testes usam fixtures em `app/tests/fixtures/`. O que depender de acesso ao vivo vira `TODO(humano)`, nunca código especulativo.
6. **Segurança:** Nunca commite `.env`, `dbt/profiles.yml`, dumps, zips ou credenciais; nunca imprima segredos em logs; TLS sempre validado (nada de `verify=False`).
7. **Irreversível = humano:** Não execute DROP/DELETE de dados, remoção de tabelas, reescrita de histórico nem rotação de credenciais. Prepare script e documentação e deixe para o humano.
8. **Compatibilidade Power BI:** Não renomeie nem remova colunas existentes de `silver.jobs`, `gold.mart_vagas` e do Excel; colunas novas entram no final. Se mudar contrato (`JobSchema`, `ScrapeResult`, `select_bronze_jobs`), atualize todos os dependentes no mesmo PR.
9. **dbt:** Não adicione pacotes externos (nada de `dbt deps`); use macros e testes próprios. Todo modelo novo tem `description`, grão explícito e testes `unique`/`not_null` na chave. No Postgres, regex usa `\y` e `(?i)`. Rode `python app/run_dbt.py build` quando houver PostgreSQL.
10. **Decisões já tomadas:** Campo sem informação = `NULL` (nunca "Não informado"); medalhão com Bronze em Python e Silver/Gold em dbt; execução em lote; TLS validado; tabela legada `jobs` só sai com aprovação humana (item 7). A única decisão que este trabalho revisa é a de descartar vagas no scraper (item 5).
11. **Armadilhas conhecidas:** Na Bronze, `flush()` das runs antes das observações (FK composta sem `relationship()`); `to_excel` do pandas 3 rejeita datetime com fuso (converta para America/Sao_Paulo e remova o fuso); no dbt, `--project-dir` e `--profiles-dir` são opções do subcomando; nunca altere o card do BeautifulSoup antes de salvar o `raw_payload`; no PowerShell, `>` grava UTF-16 (use `-f` em `pg_dump`/`psql`).
12. **Portabilidade e idioma:** Código e scripts funcionam em Windows e Linux (`pathlib`, nada exclusivo de um SO); documente comandos em PowerShell e bash. PT-BR em documentação, commits, comentários e mensagens.
13. **Na dúvida:** Escolha a opção mais conservadora e reversível, registre ADR curto em `docs/decisions/` (contexto, decisão, alternativas, consequências) e siga. Não invente fatos sobre arquivos que não leu.
14. **Docs junto com o código:** Atualize a documentação no mesmo commit que muda o comportamento. Não escreva números fixos (testes passando, linhas de código) na documentação.

---

## Comandos de Teste

### Windows (PowerShell)

```powershell
# Testes unitários (sem PostgreSQL)
cd app
python -m pytest tests/ -m "not integration" -q --tb=short

# Testes de integração (requer PostgreSQL e variável de ambiente)
$env:DATABASE_URL = "postgresql+psycopg://usuario:senha@host:5432/banco_teste"
python -m pytest tests/integration/ -m integration -q --tb=short

# Cobertura (opcional)
python -m pytest tests/ -m "not integration" --cov=app --cov-report=term-missing
```

### Linux/macOS (bash)

```bash
# Testes unitários (sem PostgreSQL)
cd app
python -m pytest tests/ -m "not integration" -q --tb=short

# Testes de integração (requer PostgreSQL e variável de ambiente)
export DATABASE_URL="postgresql+psycopg://usuario:senha@host:5432/banco_teste"
python -m pytest tests/integration/ -m integration -q --tb=short

# Cobertura (opcional)
python -m pytest tests/ -m "not integration" --cov=app --cov-report=term-missing
```

---

## Comandos de Lint/Format

### Windows (PowerShell)

```powershell
# Verificar (sem alterar)
ruff check app/

# Corrigir automaticamente (safe fixes)
ruff check app/ --fix

# Formatar
ruff format app/
```

### Linux/macOS (bash)

```bash
# Verificar (sem alterar)
ruff check app/

# Corrigir automaticamente (safe fixes)
ruff check app/ --fix

# Formatar
ruff format app/
```

---

## Comandos dbt

### Windows (PowerShell)

```powershell
# Build completo (modelos + testes) — requer PostgreSQL configurado no .env
cd app
python run_dbt.py build

# Apenas source freshness
python run_dbt.py source freshness

# Docs (gera site estático em target/)
python run_dbt.py docs generate

# Compilar SQL (validação sintática)
python run_dbt.py compile
```

### Linux/macOS (bash)

```bash
# Build completo (modelos + testes) — requer PostgreSQL configurado no .env
cd app
python run_dbt.py build

# Apenas source freshness
python run_dbt.py source freshness

# Docs (gera site estático em target/)
python run_dbt.py docs generate

# Compilar SQL (validação sintática)
python run_dbt.py compile
```

---

## Comandos do Pipeline

### Windows (PowerShell)

```powershell
# Ingestão única (scrape → raw.job_observations)
python app/main.py

# Transformação (dbt build: raw → Silver → Gold)
python app/transform.py

# Exportação Excel (gold.mart_vagas → data/exports/vagas.xlsx)
python app/export_excel.py

# Scheduler (diário às 06:00 São Paulo, com transformação)
python app/scheduler.py --com-transformacao

# Scheduler (apenas ingestão)
python app/scheduler.py
```

### Linux/macOS (bash)

```bash
# Ingestão única (scrape → raw.job_observations)
python app/main.py

# Transformação (dbt build: raw → Silver → Gold)
python app/transform.py

# Exportação Excel (gold.mart_vagas → data/exports/vagas.xlsx)
python app/export_excel.py

# Scheduler (diário às 06:00 São Paulo, com transformação)
python app/scheduler.py --com-transformacao

# Scheduler (apenas ingestão)
python app/scheduler.py
```

---

## Entry Points (após `pip install -e .`)

```bash
hub-vagas-ingest      # = python app/main.py
hub-vagas-transform   # = python app/transform.py
hub-vagas-scheduler   # = python app/scheduler.py
```

---

## Variáveis de Ambiente Principais (.env)

```env
# Banco de dados
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hub_vagas

# Ou use DATABASE_URL (tem prioridade)
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Notificações (opcional)
NOTIFICACAO_WEBHOOK_URL=https://...
SMTP_HOST=smtp.exemplo.com
SMTP_USER=usuario
SMTP_PASS=senha
NOTIFICACAO_EMAIL_FROM=remetente@exemplo.com
NOTIFICACAO_EMAIL_TO=destinatario@exemplo.com

# Scrapers
GUPY_ENABLED=false
MAX_DETAIL_PAGES=5
SCRAPER_USER_AGENT="HubVagas/1.0 (+https://github.com/Willian-Cruz/hub_vagas)"

# Relevância
RELEVANCE_MODE=silver  # silver | scraper (legacy)

# Legacy
ENABLE_LEGACY_JOBS=true
```

---

## Estrutura de Branches para Este Trabalho

| Fase | Branch | Descrição |
|------|--------|-----------|
| 0 | `melhorias/fase-0-preparacao` | Baseline, inventário, checklist, AGENTS.md |
| 1 | `melhorias/fase-1-seguranca-docs` | Itens 18, 6a, 1, 2, 4, 20 |
| 2 | `melhorias/fase-2-schema-qualidade` | Itens 8, 3, 5 |
| 3 | `melhorias/fase-3-coleta-operacao` | Itens 10, 9, 6b, 11 |
| 4 | `melhorias/fase-4-modelo-analitico` | Itens 14, 13, 12, 16, 15, 17 |
| 5 | `melhorias/fase-5-simplificacao` | Itens 7, 19 |

---

## Relatório de Fase (Template)

Ao final de cada fase, inclua no PR/relatório:

1. **Itens concluídos** (com commits), parciais e bloqueados, com motivo.
2. **Testes executados:** comando, resultado (passed/failed/skipped) e o que NÃO pôde ser executado.
3. **Decisões e suposições** (links para ADRs em `docs/decisions/`).
4. **Divergências entre documentação e código.**
5. **Novos `TODO(humano)`.**
6. **Riscos e sugestão do próximo passo.**