-- Teste de saúde do parser: detecta quedas bruscas no preenchimento de campos.
--
-- Falha (severity: warn) quando o % não-nulo de hoje cai mais de 20 pontos
-- percentuais frente à mediana dos últimos 7 dias (excluindo hoje), OU quando
-- o volume de vagas encontradas hoje cai abaixo de 50% da média semanal.
--
-- Combina com bronze.scrape_runs (monitoramento que já temos).
with hoje as (
    select
        fonte,
        campo,
        data_coleta,
        pct_nao_nulo,
        total_vagas
    from {{ ref('mart_qualidade_campos') }}
    where data_coleta = (select max(data_coleta) from {{ ref('mart_qualidade_campos') }})
),
historico as (
    select
        fonte,
        campo,
        percentile_cont(0.5) within group (order by pct_nao_nulo) as mediana_pct_7d,
        avg(total_vagas) as media_vagas_7d
    from {{ ref('mart_qualidade_campos') }}
    where data_coleta < (select max(data_coleta) from {{ ref('mart_qualidade_campos') }})
      and data_coleta >= (select max(data_coleta) from {{ ref('mart_qualidade_campos') }}) - interval '7 days'
    group by fonte, campo
),
quedas as (
    select
        h.fonte,
        h.campo,
        h.mediana_pct_7d,
        j.pct_nao_nulo as pct_hoje,
        round((h.mediana_pct_7d - j.pct_nao_nulo)::numeric, 1) as pontos_perdidos,
        j.total_vagas as vagas_hoje,
        h.media_vagas_7d,
        round(100.0 * (h.media_vagas_7d - j.total_vagas)::numeric / nullif(h.media_vagas_7d, 0), 1) as pct_queda_volume
    from hoje j
    join historico h
        on h.fonte = j.fonte
       and h.campo = j.campo
    where
        -- queda de preenchimento > 20 pontos percentuais
        (h.mediana_pct_7d is not null
         and j.pct_nao_nulo is not null
         and h.mediana_pct_7d - j.pct_nao_nulo > 20)
        OR
        -- volume de vagas caiu abaixo de 50% da média semanal
        (h.media_vagas_7d is not null
         and j.total_vagas < h.media_vagas_7d * 0.5)
)
select
    fonte,
    campo,
    mediana_pct_7d,
    pct_hoje,
    pontos_perdidos,
    vagas_hoje,
    media_vagas_7d,
    pct_queda_volume
from quedas
