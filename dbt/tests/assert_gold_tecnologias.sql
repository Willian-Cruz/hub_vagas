-- Data quality: garante que a Gold tem tecnologias extraídas
-- Pelo menos 2% das vagas devem ter pelo menos uma tecnologia detectada
-- (Catho não tem descrição, reduz a taxa global)
with stats as (
    select
        count(*) as total,
        sum(case when tecnologias <> '' and tecnologias is not null then 1 else 0 end) as com_tecnologias
    from {{ ref('mart_vagas') }}
)
select
    total,
    com_tecnologias,
    round(100.0 * com_tecnologias / nullif(total, 0), 1) as pct_com_tecnologias
from stats
where com_tecnologias < total * 0.02