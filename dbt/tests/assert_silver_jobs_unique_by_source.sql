select origem, source_job_id, count(*) as registros
from {{ ref('jobs') }}
group by origem, source_job_id
having count(*) > 1
