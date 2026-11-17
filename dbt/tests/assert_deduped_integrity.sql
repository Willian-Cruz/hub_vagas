-- Teste da etapa 3 (int_jobs_deduped): verifica que cada dedup_group_id tem
-- exatamente uma linha canônica, que first_seen_at <= last_seen_at, e que
-- dedup_group_id não é nulo.
select dedup_group_id
from {{ ref('int_jobs_deduped') }}
group by dedup_group_id
having sum(case when is_canonical then 1 else 0 end) <> 1

union all

select dedup_group_id
from {{ ref('int_jobs_deduped') }}
where first_seen_at > last_seen_at

union all

select dedup_group_id
from {{ ref('int_jobs_deduped') }}
where dedup_group_id is null
