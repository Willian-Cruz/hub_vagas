-- Teste da etapa 2 (int_jobs_normalized): verifica que senioridade só contém
-- valores válidos ou NULL, e que não há duplicatas de raw_job_id.
select raw_job_id
from {{ ref('int_jobs_normalized') }}
where senioridade is not null
  and senioridade not in (
      'Estágio/Trainee', 'Júnior', 'Pleno', 'Sênior', 'Especialista',
      'Coordenador', 'Liderança', 'Diretoria', 'Técnico'
  )

union all

select raw_job_id
from (
    select raw_job_id
    from {{ ref('int_jobs_normalized') }}
    group by raw_job_id
    having count(*) > 1
) dup
