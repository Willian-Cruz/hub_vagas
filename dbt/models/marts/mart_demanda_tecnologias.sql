-- Gold: mart_demanda_tecnologias — contagem de vagas por tecnologia monitorada.
--
-- A lista de tecnologias vem da seed dbt/seeds/tecnologias_monitoradas.csv
-- (fonte única, compartilhada com o Python via tech_service.TECNOLOGIAS).
with tecnologias as (
    select tecnologia from {{ ref('tecnologias_monitoradas') }}
),
mentions as (
    select
        t.tecnologia as tecnologia,
        j.origem as origem,
        j.link as link
    from {{ ref('jobs') }} as j
    cross join tecnologias as t
    where coalesce(j.descricao, '') ~* ('\m' || t.tecnologia || '\M')
)
select
    tecnologia,
    count(distinct link) as vagas_com_mencao,
    count(distinct origem) as fontes,
    current_timestamp as atualizado_em
from mentions
group by tecnologia
