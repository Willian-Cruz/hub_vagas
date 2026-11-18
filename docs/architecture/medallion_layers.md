# Camadas Medallion — Hub Vagas

Este documento define as camadas de dados do projeto seguindo o padrão **Medallion**
adaptado à realidade do hub_vagas.

> **Importante:** não confunda a arquitetura Medallion com a mera criação de
> schemas chamados `raw`, `bronze`, `silver` e `gold`. Cada camada tem uma
> responsabilidade real. A `bronze.scrape_runs` é metadado operacional de
> execução, não uma camada de dados de negócio.

---

## Resumo das camadas

| Camada | Schema | Tabela/Modelo | Materialização | Responsabilidade |
|--------|--------|---------------|----------------|------------------|
| **Ingestão** | — | Scrapers Python | — | Coletar vagas dos portais, aplicar contrato NULL e filtro de relevância |
| **Raw** | `raw` | `raw.job_observations` | Tabela (append-only) | Landing zone com payload JSONB bruto, dedup por payload_hash |
| **Bronze** | `bronze` | `bronze.scrape_runs` | Tabela (append-only) | Metadado operacional de execução (freshness, status, contagens) |
| **Silver** | `silver` | `silver.jobs` | Tabela (via dbt) | Normalização, dedup, validação de NULLs, enriquecimento controlado |
| **Gold** | `gold` | `gold.mart_*` | Tabelas (via dbt) | Indicadores analíticos agregados para consumo |

---

## Raw — `raw.job_observations`

**Propriedades:**
- Append-only: nenhuma linha é apagada ou sobrescrita.
- Uma linha por observação de coleta (mesma vaga coletada 2 vezes = 2 linhas).
- Payload bruto em JSONB, exatamente como veio do scraper.

**Responsabilidade:** ser a fonte da verdade imutável para todo reprocessamento futuro. Se uma regra de normalização mudar, basta rodar `dbt seed` + `dbt build` para rederivar a Silver a partir da raw.

**Colunas de linhagem (M09):** `id`, `run_id`, `source`, `source_job_id`, `collected_at`, `ingested_at`, `scraper_version`, `payload_hash`.

---

## Bronze — `bronze.scrape_runs`

**Propriedades:**
- Append-only: snapshot de cada execução por fonte.
- Não armazena vagas, apenas metadado de execução.

**Responsabilidade:** monitoramento de freshness (warn 24h / error 72h) e auditoria de execuções. **Não é uma camada de dados de negócio.**

> Uma "Bronze de negócio" é opcional. Só deve ser criada se houver necessidade concreta (ex.: dados intermediários que precisam ser compartilhados entre pipelines sem passar pelo dbt).

---

## Silver — `silver.jobs`

**Propriedades:**
- Todas as linhas da raw são mantidas (nenhuma apagada).
- Dedup por grupo de conteúdo: `dedup_group_id` + `is_canonical`.
- Apenas linhas canônicas (`is_canonical = true`) vão para os marts Gold.

**Transformações:**
- `null_if_placeholder`: textos tipo "Confidencial", "Localização não informada" → `NULL`.
- `normalize_seniority` + `classify_seniority_cascade`: única fonte de verdade para senioridade.
- `extract_salary`: `salario_texto`, `salario_min`, `salario_max`, `salario_tipo`.
- `normalize_location`: preposições minúsculas, padrão "Cidade - UF".
- `data_publicacao_precisao`: `hora` / `dia` / `estimada`.
- `dias_no_ar`, `is_ativa`.

**Linhagem (M09):** `run_id`, `scraper_version`, `ingested_at` propagados da raw. `senioridade_inferida` e `salario_inferido` indicam quando o campo foi derivado.

---

## Gold — `gold.mart_*`

**Propriedades:**
- Tabelas recriadas a cada `dbt build`.
- Grants `select` para `bi_reader` (Power BI).
- Agregados a partir do Silver (apenas `is_canonical = true`).

**Marts:**
- `mart_vagas`: base principal para exportação e dashboard.
- `mart_salarios`: cobertura salarial por origem e senioridade (média, mediana).
- `mart_demanda_tecnologias`: ranking de tecnologias (25 termos da seed).
- `mart_vagas_por_dia`: tendência de volume com `pct_com_descricao_completa`.
- `mart_status_fontes`: monitoramento de freshness.
- `mart_qualidade_campos`: saúde do parser por fonte/campo.

---

## Fluxo conceitual

```
Raw (payload bruto JSONB)
    │
    ▼ dbt build: staging → unioned → normalized → deduped
Silver (normalizado, deduplicado, is_canonical)
    │
    ▼ dbt build: marts agregados
Gold (indicadores analíticos)
    │
    ▼ consumo
Power BI / Excel
```
