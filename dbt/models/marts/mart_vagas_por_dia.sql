-- Gold: mart_vagas_por_dia — volume de observações coletadas por dia e portal.
-- Lê da Silver ({{ ref('jobs') }}), não do raw, para reconciliar com mart_vagas.
select
    (data_coleta at time zone 'America/Sao_Paulo')::date as data_coleta,
    origem as source,
    count(*) as observacoes,
    count(distinct link) as vagas_distintas,
    sum(case when is_canonical then 1 else 0 end) as vagas_canonicas,
    round(
        100.0 * sum(case when not descricao_truncada then 1 else 0 end)
        / nullif(count(*), 0),
        1
    ) as pct_com_descricao_completa
from {{ ref('jobs') }}
group by (data_coleta at time zone 'America/Sao_Paulo')::date, origem
