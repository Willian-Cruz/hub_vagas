with tecnologias (tecnologia) as (
    {{ monitored_technologies() }}
),

mentions as (
    select
        tecnologia,
        origem,
        link
    from {{ ref('jobs') }}
    cross join tecnologias
    where coalesce(descricao, '') ~* ('\m' || tecnologia || '\M')
)

select
    tecnologia,
    count(distinct link) as vagas_com_mencao,
    count(distinct origem) as fontes,
    current_timestamp as atualizado_em
from mentions
group by tecnologia
