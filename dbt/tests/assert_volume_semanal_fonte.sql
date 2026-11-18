{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Falha se jobs_found de uma fonte está abaixo de '
                      'volume_min_pct_media_semanal% da média semanal da fonte. '
                      'Limiar em vars do dbt_project.yml.'
    }
  )
}}

-- Compara o jobs_found mais recente de cada fonte contra a média dos últimos 7 dias.
-- Falha quando o valor atual está abaixo do limiar percentual da média.
with ultimos_dados as (
    select
        source as fonte,
        finished_at,
        jobs_found,
        row_number() over (partition by source order by finished_at desc) as rn
    from {{ source('bronze', 'scrape_runs') }}
    where status in ('success', 'partial')
),
mais_recente as (
    select fonte, jobs_found as vagas_hoje, finished_at as data_atual
    from ultimos_dados
    where rn = 1
),
media_semanal as (
    select
        fonte,
        avg(jobs_found) as media_semanal
    from ultimos_dados
    where rn > 1
      and finished_at >= (select max(finished_at) from {{ source('bronze', 'scrape_runs') }}) - interval '7 days'
    group by fonte
)
select
    m.fonte,
    m.vagas_hoje,
    round(s.media_semanal, 1) as media_semanal,
    round(100.0 * m.vagas_hoje / nullif(s.media_semanal, 0), 1) as pct_da_media,
    {{ var('volume_min_pct_media_semanal', 50) }} as limiar_pct
from mais_recente m
join media_semanal s
    on m.fonte = s.fonte
where m.vagas_hoje < s.media_semanal * {{ var('volume_min_pct_media_semanal', 50) }} / 100.0
