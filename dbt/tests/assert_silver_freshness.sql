{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Invariante de frescor: a Silver deve refletir uma coleta bem-sucedida recente. '
                      'Alinha-se aos limiares de sources.yml (warn 24h / error 72h). '
                      'Falha (error) quando a última coleta com status=success tem mais de 72h; '
                      'o warn em 24h é emitido por `dbt source freshness` sobre as fontes.'
    }
  )
}}

-- Data quality: verifica se a Silver foi atualizada a partir de uma coleta
-- bem-sucedida recente.
--
-- Mede a última coleta com status = 'success' em bronze.scrape_runs (não a
-- última tentativa, que pode ser failed/empty/partial). Alinha os limiares a
-- sources.yml: warn 24h / error 72h.
with ultima_coleta_sucesso as (
    select max(finished_at) as ultima
    from {{ source('bronze', 'scrape_runs') }}
    where status = 'success'
)
select
    ultima as ultima_coleta_sucesso,
    current_timestamp as agora,
    extract(epoch from (current_timestamp - ultima)) / 3600 as horas_desde_coleta,
    72 as limite_error_horas,
    24 as limite_warn_horas
from ultima_coleta_sucesso
where ultima is null
   or ultima < current_timestamp - interval '72 hours'
