-- Teste da etapa 3 (int_jobs_deduped): verifica que cada dedup_group_id tem
-- exatamente uma linha canônica (is_canonical = true).
with grupos_sem_canonica as (
    select dedup_group_id, count(*) as n_canonicas
    from {{ ref('int_jobs_deduped') }}
    group by dedup_group_id
    having sum(case when is_canonical then 1 else 0 end) <> 1
)
select * from grupos_sem_canonica

union all

-- first_seen_at deve ser <= last_seen_at
select
    'intervalo_invalido' as erro,
    count(*) as n
from {{ ref('int_jobs_deduped') }}
where first_seen_at > last_seen_at

union all

-- dedup_group_id não pode ser nulo
select
    'dedup_group_id_nulo' as erro,
    count(*) as n
from {{ ref('int_jobs_deduped') }}
where dedup_group_id is null
