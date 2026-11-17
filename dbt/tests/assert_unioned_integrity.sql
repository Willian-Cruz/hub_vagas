-- Teste da etapa 1 (int_jobs_unioned): verifica que não há títulos ou links nulos
-- na união, e que não há raw_job_id duplicado. Retorna 0 linhas quando tudo OK.
select raw_job_id
from {{ ref('int_jobs_unioned') }}
where titulo is null or link is null

union all

select raw_job_id
from (
    select raw_job_id
    from {{ ref('int_jobs_unioned') }}
    group by raw_job_id
    having count(*) > 1
) dup
