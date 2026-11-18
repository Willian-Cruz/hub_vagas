# ADR 0001 — `jobs` como raw: `raw_payload`, `first_seen_at`, `last_seen_at`

## Contexto

O hub_vagas coleta vagas de múltiplos portais (Vagas.com, InfoJobs, Catho,
Gupy) e as transforma com dbt (Silver → Gold). Inicialmente a tabela raw
`public.jobs` guardava apenas campos escalares extraídos do card (título,
empresa, local, salário etc.) e descartava vagas repetidas por heurística de
dedup (mesmo link ou mesmo `(origem, id_externo)`).

Dois problemas decorriam disso:

1. **Sem payload bruto:** quando o HTML do card mudava (ex.: salário aparecendo
   depois, nova modalidade), não havia como reprocessar a vaga com uma regra
   nova, porque o original já havia sido sobrescrito ou descartado.
2. **Sem histórico de presença:** uma vaga repetida era descartada no log, sem
   registrar que ela continua no ar. Não era possível medir `dias_no_ar` nem
   separar vagas "novas" de vagas "revistas" nas métricas do pipeline.

A migração `006` criou a tabela `raw.job_observations` (append-only) com
`raw_payload JSONB` e `payload_hash`, preservando o fragmento HTML do card e
permitindo dedup por conteúdo idêntico. A tabela `public.jobs` ficou como
legado da migração `004`.

## Decisão

A fonte de dados bruta (raw) é a tabela `raw.job_observations`, populada pelos
scrapers via `JobRepository.salvar()`. Cada execução gera uma nova linha por
vaga coletada, contendo:

- `raw_payload JSONB`: fragmento HTML do card + campos extras (`html_fragment`,
  `senioridade_origem`, etc.), exatamente como vieram do scraper.
- `payload_hash`: SHA-256 do payload, usado para detectar retransmissão
  idêntica (não reinsere se o payload não mudou).
- `is_relevant`: resultado do filtro de relevância (ADR 0002).

O Python é responsável **apenas pela ingestão**: extrair os campos do card e
gravar na raw, sem aplicar normalização de negócio (senioridade, local,
salário, modalidade, tecnologias ficam para o dbt).

### `first_seen_at` e `last_seen_at`

São computados na camada Silver (dbt, `int_jobs_deduped`) como `min(data_coleta)`
e `max(data_coleta)` por `dedup_group_id`. Uma vaga republicada com outro ID
continua no mesmo grupo (chave de conteúdo: portal + título + empresa + local).
Assim `first_seen_at` é imutável e `last_seen_at` é atualizado a cada nova
observação do mesmo grupo.

A dedup é **por portal**: a mesma vaga em dois portais conta duas vezes. Nenhuma
linha é apagada; todas são mantidas com `dedup_group_id`, `first_seen_at`,
`last_seen_at` e `is_canonical` (marca a linha mais recente do grupo). Os
martes Gold usam apenas `is_canonical = true`.

### `dias_no_ar` e `is_ativa`

- `dias_no_ar = extract(epoch from (last_seen_at - first_seen_at)) / 86400`:
  NULL quando o grupo tem uma única observação.
- `is_ativa = true` quando `last_seen_at` está nos últimos 3 dias (janela
  configurável), caso contrário `false`.

### Tabela `public.jobs` (legado)

Mantida como legado da migração `004`; não é mais gravada pelo Python. O dbt
lê de `raw.job_observations` através da fonte `raw_observations.job_observations`
declarada em `dbt/models/sources.yml`.

### Tabela `bronze.scrape_runs`

Snapshot append-only de execução por fonte (monitoramento de freshness). **Não
é uma camada de dados de vagas**; alimenta apenas `mart_status_fontes`.

## Consequências

- É possível reprocessar vagas antigas quando uma regra de normalização muda,
  porque o `raw_payload` original está preservado.
- `dias_no_ar` fica disponível na Silver para análise de tempo de permanência
  da vaga no ar.
- Métricas do pipeline separam "novas" (primeira observação do grupo) de
  "revistas" (observação subsequente do mesmo grupo, com payload diferente).
- Nenhuma linha é perdida por dedup heurística; a deduplicação é explícita via
  `is_canonical` na Silver.
- O custo de armazenamento cresce com o número de observações (tabela
  append-only), não com o número de vagas distintas.

## ADRs relacionados

- ADR 0002 — Destino do filtro de relevância (Opção A: salvar tudo com
  `is_relevant`, Silver filtra).
