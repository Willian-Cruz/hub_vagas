-- Teste da etapa 1 (int_jobs_unioned): verifica que a união preserva todas as linhas
-- dos staging (sem descartar por dedup) e que não há títulos ou links nulos.
with contagem_unioned as (
    select count(*) as total_unioned from {{ ref('int_jobs_unioned') }}
),
contagem_staging as (
    select (
        (select count(*) from {{ ref('stg_vagas_com_jobs') }}) +
        (select count(*) from {{ ref('stg_infojobs_jobs') }}) +
        (select count(*) from {{ ref('stg_gupy_jobs') }}) +
        (select count(*) from {{ ref('stg_catho_jobs') }})
    ) as total_staging
)
select
    u.total_unioned,
    s.total_staging,
    u.total_unioned - s.total_staging as diferenca
from contagem_unioned u, contagem_staging s
where u.total_unioned <> s.total_staging

union all

-- Linhas com título ou link nulo não devem existir na união (descartadas no cleaned)
select
    count(*) as linhas_com_titulo_ou_link_nulo,
    null,
    null
from {{ ref('int_jobs_unioned') }}
where titulo is null or link is null
