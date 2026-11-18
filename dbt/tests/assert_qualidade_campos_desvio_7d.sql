{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Falha se o % não-nulo de um campo cai mais de '
                      'qualidade_desvio_max_pontos pontos percentuais frente '
                      'à mediana dos últimos 7 dias. Limiar em vars do dbt_project.yml.'
    }
  )
}}

-- Compara o pct_nao_nulo mais recente de cada (fonte, campo) contra a mediana
-- dos últimos 7 dias. Falha quando o desvio excede o limiar configurado.
with ultimos_dados as (
    select
        fonte,
        campo,
        data_coleta,
        pct_nao_nulo,
        row_number() over (partition by fonte, campo order by data_coleta desc) as rn
    from {{ ref('mart_qualidade_campos') }}
),
mais_recente as (
    select fonte, campo, pct_nao_nulo as pct_atual, data_coleta as data_atual
    from ultimos_dados
    where rn = 1
),
janela_7dias as (
    select
        fonte,
        campo,
        percentile_cont(0.5) within group (order by pct_nao_nulo) as pct_mediana_7d
    from ultimos_dados
    where rn > 1
      and data_coleta >= (select max(data_coleta) from {{ ref('mart_qualidade_campos') }}) - interval '7 days'
    group by fonte, campo
)
select
    m.fonte,
    m.campo,
    m.pct_atual,
    j.pct_mediana_7d,
    round((m.pct_atual - j.pct_mediana_7d)::numeric, 1) as desvio_pontos,
    {{ var('qualidade_desvio_max_pontos', 10) }} as limiar_pontos
from mais_recente m
join janela_7dias j
    on m.fonte = j.fonte
   and m.campo = j.campo
where m.pct_atual < j.pct_mediana_7d - {{ var('qualidade_desvio_max_pontos', 10) }}
