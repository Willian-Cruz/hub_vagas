# ADR-001 — Organização das camadas de dados

## Contexto

O hub_vagas coleta vagas de múltiplos portais (Vagas.com, InfoJobs, Gupy, Catho)
e as transforma com dbt (Silver → Gold). Inicialmente, o projeto misturava
conceitos: a tabela `bronze.scrape_runs` era tratada como se fosse uma camada
de dados de negócio, e a raw `public.jobs` não guardava payload bruto nem
histórico de presença.

Havia confusão entre "criar schemas chamados raw/bronze/silver/gold" e
"implementar uma arquitetura Medallion com responsabilidades claras por camada".

## Decisão

Definir as camadas com responsabilidades distintas:

| Camada | Tabela/Modelo | Responsabilidade |
|--------|---------------|------------------|
| **Ingestão** | Scrapers Python | Coletar vagas, aplicar contrato NULL, filtro de relevância |
| **Raw** | `raw.job_observations` | Landing zone append-only, payload JSONB, dedup por payload_hash |
| **Bronze** | `bronze.scrape_runs` | Metadado operacional de execução (freshness), **não** dados de negócio |
| **Silver** | `silver.jobs` | Normalização, dedup, validação NULL, enriquecimento controlado |
| **Gold** | `gold.mart_*` | Indicadores analíticos agregados |

### bronze.scrape_runs

Mantida como está. Armazena identificador da execução, horário de início/fim,
fonte processada, status da coleta, quantidade de registros e mensagens de erro.
É uma tabela de controle operacional, não uma tabela Bronze de negócio. Não será
movida para outra camada automaticamente.

### Nenhuma "Bronze de negócio" será criada

A menos que surja uma necessidade concreta, não será criada uma camada Bronze
de negócio separada. O fluxo vai direto da raw para a Silver via dbt.

## Alternativas consideradas

1. **Manter `bronze.scrape_runs` como camada de dados:** Rejeitado. Ela armazena metadado de execução, não vagas. Confundiria a arquitetura.
2. **Criar Bronze de negócio:** Rejeitado. Sem necessidade concreta, adicionaria complexidade sem benefício.
3. **Usar apenas raw e silver (sem bronze):** Rejeitado. O bronze.scrape_runs serve para freshness e auditoria, mantê-lo é útil.

## Justificativa

Evitar camadas redundantes e manter responsabilidades claras facilita a
manutenção, o teste e a expansão do projeto. Qualquer desenvolvedor novo
consegue entender onde cada dado está e por quê.

## Consequências

- Fluxo de dados simplificado: raw → Silver → Gold.
- Maior clareza arquitetural documentada em `ARCHITECTURE.md`.
- `bronze.scrape_runs` documentada explicitamente como metadado operacional.

## ADRs relacionados

- `0001-jobs-como-raw.md` — decisão de usar `raw.job_observations` como raw.
- `0002-filtro-de-relevancia.md` — decisão Opção A (salvar tudo, Silver filtra).
