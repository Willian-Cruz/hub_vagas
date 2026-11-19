# Observabilidade — Hub Vagas

Este documento descreve como o pipeline é monitorado: logs estruturados,
métricas de execução, indicadores de freshness e qualidade, visão consolidada
de saúde e condições de alerta.

---

## 1. Logs estruturados (M13)

Todos os logs do pipeline são emitidos em formato JSON estruturado (uma linha
por evento), permitindo filtragem por `run_id`, `source`, `component`, `stage`,
`event` e `status`.

### Campos do log estruturado

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `timestamp` | string (ISO 8601) | Momento do evento (UTC) |
| `level` | string | Nível do log: INFO, WARNING, ERROR |
| `run_id` | string | UUID da execução de coleta (linhagem) |
| `source` | string | Nome do portal (Vagas.com, InfoJobs, Gupy, Catho) |
| `component` | string | Componente que gerou o evento (scraper, repository, pipeline, dbt) |
| `stage` | string | Etapa do pipeline (coleta, persistencia, transformacao, exportacao) |
| `event` | string | Nome do evento (vagas_coletadas, vaga_inserida, dbt_build_concluido, etc.) |
| `status` | string | Resultado: sucesso, falha, parcial, vazio |
| `duration_ms` | number | Duração da etapa em milissegundos |
| `records_received` | number | Registros recebidos na etapa |
| `records_persisted` | number | Registros persistidos no banco |
| `records_rejected` | number | Registros rejeitados |
| `error_type` | string | Tipo de erro (se houver) |
| `error_message` | string | Mensagem de erro (sem secrets) |
| `mensagem` | string | Texto livre adicional |

### Uso no código

```python
from utils.logger import get_logger, log_event

logger = get_logger(__name__)

log_event(
    logger=logger,
    level="INFO",
    run_id=str(run_id),
    source="Vagas.com",
    component="scraper",
    stage="coleta",
    event="source_completed",
    status="sucesso",
    duration_ms=1250,
    records_received=28,
    records_persisted=28,
    records_rejected=0,
)
```

**Nunca registre secrets, senhas, tokens ou payloads completos nos logs.**

---

## 2. Métricas de execução

O `PipelineService.executar()` retorna um dicionário com métricas completas:

| Métrica | Descrição |
|---------|-----------|
| `run_id` | UUID da execução |
| `status` | SUCESSO, PARCIAL ou FALHADO |
| `started_at` | ISO-8601 UTC do início |
| `finished_at` | ISO-8601 UTC do término |
| `duration_seconds` | Duração em segundos |
| `sources_total` | Total de fontes consultadas |
| `sources_success` | Fontes com status SUCCESS |
| `sources_failed` | Fontes com status FAILED |
| `records_received` | Total de vagas recebidas dos scrapers |
| `records_validated` | Vagas que passaram na validação de contrato |
| `records_inserted` | Vagas novas inseridas na raw |
| `records_updated` | Vagas revistas na raw |
| `records_duplicated` | Vagas duplicadas ignoradas |
| `records_rejected` | Vagas rejeitadas (erro de persistência) |
| `raw_errors` | Erros de persistência na raw |
| `dbt_status` | `"nao_executado"` (dbt é etapa separada) |
| `error_stage` | Etapa onde ocorreu erro, se houver |
| `bronze_ok` | Se o bronze.scrape_runs foi gravado |
| `fontes_sucesso` | Fontes com status SUCCESS |
| `fontes_parcial` | Fontes com status PARTIAL |
| `fontes_falha` | Fontes com status FAILED |
| `fontes_vazio` | Fontes com status EMPTY |
| `descartadas` | Vagas fora do tema (filtro de relevância) |
| `duracao_seg` | Duração total da execução (em segundos) |
| `bloqueado_por_trava` | Se foi bloqueado pelo advisory lock |
| `sucesso` | True se status == SUCCESS |
| `bloqueado_por_trava` | Se foi bloqueado pelo advisory lock |

---

## 3. Freshness (atualidade dos dados)

A freshness é monitorada em duas camadas:

### 3.1 Fonte (bronze.scrape_runs)

Definida em `dbt/models/sources.yml` com `filter: status in ('success','partial')`:

| Limiar | Severidade | Significado |
|--------|------------|-------------|
| 24h | warn | Última coleta com sucesso/parcial há mais de 24h |
| 72h | error | Última coleta com sucesso/parcial há mais de 72h |

### 3.2 Silver (silver.jobs)

Definida em `dbt/tests/assert_silver_freshness.sql`:

| Limiar | Severidade | Significado |
|--------|------------|-------------|
| 24h | warn | Última coleta com status=success há mais de 24h |
| 72h | error | Última coleta com status=success há mais de 72h |

---

## 4. Qualidade dos dados

### 4.1 Percentual de NULL por campo

Definida em `dbt/tests/assert_silver_null_pct.sql` com limiares configuráveis via `vars`:

| Campo | Limiar (warn) | Significado |
|-------|---------------|-------------|
| empresa | 50% | Mais de 50% das vagas com empresa NULL |
| localizacao | 50% | Mais de 50% das vagas com localização NULL |
| senioridade | 30% | Mais de 30% das vagas com senioridade NULL |
| modalidade | 50% | Mais de 50% das vagas com modalidade NULL |
| salario_texto | 40% | Mais de 40% das vagas com salário NULL |
| descricao | 30% | Mais de 30% das vagas com descrição NULL |

### 4.2 Desvio vs mediana dos últimos 7 dias

Definida em `dbt/tests/assert_qualidade_campos_desvio_7d.sql`:

| Limiar | Severidade | Significado |
|--------|------------|-------------|
| 10 pontos percentuais | error | % não-nulo caiu mais de 10 pp frente à mediana dos últimos 7d |

### 4.3 Volume semanal por fonte

Definida em `dbt/tests/assert_volume_semanal_fonte.sql`:

| Limiar | Severidade | Significado |
|--------|------------|-------------|
| 50% | error | jobs_found abaixo de 50% da média semanal da fonte |

### 4.4 Regras de negócio (salário)

Definida em `dbt/tests/assert_salario_valido.sql`:

| Regra | Severidade | Significado |
|-------|------------|-------------|
| salario_min <= salario_max | error | Salário mínimo maior que o máximo |
| sem valores negativos | error | Salário negativo é inválido |
| a_combinar → ambos NULL | error | "A combinar" não deve ter valores numéricos |
| faixa → ambos preenchidos | error | Tipo faixa deve ter min e max |

---

## 5. Visão consolidada de saúde (mart_saude_pipeline)

O mart `gold.mart_saude_pipeline` reúne todos os indicadores operacionais por
fonte em uma única consulta:

```sql
select * from gold.mart_saude_pipeline;
```

| Coluna | Descrição |
|--------|-----------|
| `origem` | Nome do portal |
| `total_execucoes` | Total de execuções registradas |
| `sucessos` / `falhas` / `parciais` / `vazias` | Contagem por status |
| `pct_sucesso` / `pct_falha` | Taxa de sucesso/falha em % |
| `ultima_coleta_sucesso` | Última coleta com sucesso |
| `duracao_media_seg` | Duração média da coleta |
| `total_vagas_coletadas` | Total de vagas coletadas |
| `vagas_na_silver` / `vagas_canonicas` / `vagas_ativas` | Volume na Silver |
| `status_saude` | saudavel / falhas_intermitentes / sempre_falha / baixa_confiabilidade / dados_desatualizados / sem_coleta_sucesso |
| `ultimo_erro` | Última mensagem de erro |

### status_saude

| Valor | Condição |
|-------|----------|
| `saudavel` | ≥80% de sucesso e coleta recente |
| `falhas_intermitentes` | Tem falhas mas também sucessos |
| `sempre_falha` | Apenas falhas, nenhum sucesso |
| `baixa_confiabilidade` | Taxa de sucesso < 80% |
| `dados_desatualizados` | Último sucesso há mais de 72h |
| `sem_coleta_sucesso` | Nunca teve uma coleta com sucesso |

---

## 6. Condições de alerta

As condições abaixo devem disparar notificação (webhook Discord/Telegram ou e-mail
via `app/notifier.py`):

| Condição | Severidade | Canal | Ação |
|----------|------------|-------|------|
| Fonte sem execução no período esperado (>72h sem sucesso) | warn | Webhook/E-mail | Verificar scraper da fonte |
| Falhas consecutivas (3 execuções seguidas com status=failed) | error | Webhook/E-mail | Investigar scraper/banco |
| Queda de volume >50% frente à média semanal | error | Webhook/E-mail | Verificar portal/filtro de relevância |
| Aumento de rejeições (desvio de qualidade >10pp vs mediana 7d) | warn | Webhook/E-mail | Recalibrar parser |
| Falha crítica de persistência (raw erros > 0 em execução) | error | Webhook/E-mail | Verificar banco/conexão |
| Falha em modelos dbt (dbt build com ERROR) | error | Webhook/E-mail | Verificar modelos SQL |
| Dados desatualizados (último sucesso >72h) | warn | Webhook/E-mail | Verificar agendamento |

### Não notificar (evitar alertas excessivos)

- Fonte com status `empty` (nenhuma vaga encontrada, mas coleta funcionou)
- Primeira execução de uma fonte nova (sem histórico para comparar)
- Warnings de freshness entre 24h e 72h (apenas log, sem notificação)

---

## 7. Diagnóstico de falhas sem acessar módulos

Para identificar a origem de um problema, consulte nesta ordem:

```sql
-- 1. Estado geral do pipeline
select * from gold.mart_saude_pipeline order by pct_falha desc;

-- 2. Últimas execuções por fonte
select * from bronze.scrape_runs
order by started_at desc limit 20;

-- 3. Qualidade dos dados por fonte
select * from gold.mart_qualidade_campos
where data_coleta = (select max(data_coleta) from gold.mart_qualidade_campos)
order by pct_nao_nulo asc;

-- 4. Logs estruturados (filtrar por run_id)
-- Os logs estão em logs/pipeline.log (formato JSON, uma linha por evento)
```

Exemplo de filtro de logs por `run_id`:
```bash
grep "run_id":"<UUID>" logs/pipeline.log
```
