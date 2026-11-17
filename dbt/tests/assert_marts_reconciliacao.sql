-- Teste de reconciliação: mart_vagas (canônicas) e mart_vagas_por_dia (vagas_canonicas)
-- devem bater por origem. Se divergirem, a dedup está quebrada.
with canonicas as (
    select origem, count(*) as total_canonicas
    from {{ ref('mart_vagas') }}
    group by origem
),
por_dia as (
    select source as origem, sum(vagas_canonicas) as total_por_dia
    from {{ ref('mart_vagas_por_dia') }}
    group by source
)
select
    c.origem,
    c.total_canonicas,
    p.total_por_dia,
    abs(c.total_canonicas - p.total_por_dia) as diferenca
from canonicas c
full outer join por_dia p
    on c.origem = p.origem
where abs(coalesce(c.total_canonicas, 0) - coalesce(p.total_por_dia, 0)) > 0
