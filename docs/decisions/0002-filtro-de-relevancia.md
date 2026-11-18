# ADR 0002 — Destino do filtro de relevância (Opção A: salvar tudo, Silver filtra)

## Contexto

O filtro de relevância (`RelevanceService`) verifica se o título da vaga cita
algum termo de `dbt/seeds/termos_relevancia.csv` (dados, data, analytics, BI,
SQL, Python, etc.). Inicialmente as vagas não-relevantes são **descartadas no
scraper** (Python) antes de chegar ao banco: só as relevantes são gravadas em
`raw.job_observations`.

Isso impede responder à pergunta aberta nº 1 do RESUMO (§13):
> "Quantas vagas boas o filtro joga fora?"

Sem salvar as descartadas, não há como medir a taxa de falso-negativo nem
ajustar `termos_relevancia.csv` com base em evidência.

## Decisão

**Opção A (recomendada):** gravar **todas** as vagas coletadas em
`raw.job_observations`, com os campos `is_relevant` (boolean) e
`motivo_relevancia` (texto, preenchido apenas quando `is_relevant = false`).
A camada Silver (dbt) filtra `is_relevant = true` nos marts. O descarte
continua existindo, mas agora é visível e mensurável.

### Por que não a Opção B

A Opção B manteria o descarte no Python e gravaria apenas as descartadas em
uma tabela `bronze.descartadas(run_id, source, titulo, link, motivo)` para
auditoria. Isso resolve a parte da medição, mas impede reprocessar as
descartadas quando o filtro mudar (ex.: adicionar um novo termo de relevância).
Com a Opção A, basta mudar `termos_relevancia.csv` e rodar `dbt seed` +
`dbt build` para revisar o histórico.

### Mudanças no código

- `JobSchema`: adicionar `is_relevant: bool = True` e
  `motivo_relevancia: Optional[str] = None`.
- `RelevanceService.separar()`: deixa de dividir em duas listas. Passa a
  definir `vaga.is_relevant` e `vaga.motivo_relevancia` em cada vaga e
  devolver todas elas.
- `CollectorService`: não filtra; apenas conta `relevantes` vs `descartadas`
  para o log.
- `JobRepository.salvar()`: grava `is_relevant` e `motivo_relevancia` do
  `raw_payload` (já estão no dict do scraper) e na coluna dedicada da raw.
- Staging Silver (`stg_*_jobs`): lê `is_relevant` e `motivo_relevancia` do
  `raw_payload`.
- Silver (`int_jobs_*`): preserva `is_relevant`; os marts filtram
  `is_relevant = true`.

## Consequências

- É possível responder "quantas vagas boas o filtro descartou na última semana?"
  com uma consulta à Silver: `count(*) where is_relevant = false`.
- Reprocessar quando o filtro mudar: não é necessário coletar novamente, basta
  `dbt seed` + `dbt build`.
- `raw.job_observations` cresce mais (todas as vagas, não só as relevantes),
  mas é append-only e o custo de armazenamento é baixo.
- `motivo_relevancia` ajuda a diagnosticar falsos-negativos (ex.: título com
  sigla não mapeada no CSV).
