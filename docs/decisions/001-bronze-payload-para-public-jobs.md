# ADR 001 — Bronze de payload (JSONB) → public.jobs

## Contexto

Inicialmente o hub_vagas gravava o payload bruto de cada coleta em uma tabela
append-only do esquema `bronze` (`bronze.job_observations`, coluna `source_payload`
JSONB), e o dbt transformava esse JSONB nas camadas Silver e Gold.

Na refatoração de desacoplamento entre ingestão e transformação (etapa 14 do
histórico do README), o Python passou a gravar direto na tabela raw `public.jobs`
(landing zone) e o dbt passou a ler dela. A tabela `bronze.job_observations`
ficou sem consumidores e foi removida pela migração `005`.

## Decisão

A fonte de dados bruta é a tabela `public.jobs`, populada pelos scrapers via
`JobRepository.salvar()`. O Python é responsável **apenas pela ingestão**:
extrair os campos do card do portal e gravar na raw `jobs`, sem aplicar
normalização de negócio (senioridade, local, salário, modalidade, tecnologias).

Todas as transformações (NULL de placeholders, deduplicação, normalização de
senioridade/local/salário/modalidade, extração de tecnologias) são de
responsabilidade do dbt, em `dbt/models/staging/`, `dbt/models/intermediate/`
e `dbt/models/marts/`.

A tabela `bronze.scrape_runs` é mantida como snapshot append-only de execução
por fonte (monitoramento de freshness), mas não é fonte dos dados de vagas.

## Consequências

- `bronze.job_observations` não existe mais (removida pela migration `005`).
- O dbt lê de `public.jobs` através da fonte `raw.jobs` declarada em
  `dbt/models/sources.yml` (schema `public`, tabela `jobs`).
- `JobRepository.salvar()` não normaliza mais campos; grava os valores conforme
  vieram do scraper, preenchendo apenas campos NULL de duplicatas.
- O contrato "campo sem informação é NULL" é aplicado na Silver pelo dbt, não
  no Python.
- Não há payload JSONB original preservado na raw; reexecutar uma coleta não
  recupera o HTML/cartão original do portal.
