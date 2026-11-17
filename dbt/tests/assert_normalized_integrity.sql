-- Teste da etapa 2 (int_jobs_normalized): verifica que senioridade só contém
-- valores válidos ou NULL, e que não há duplicatas de raw_job_id.
with valores_invalidos as (
    select senioridade, count(*) as n
    from {{ ref('int_jobs_normalized') }}
    where senioridade is not null
      and senioridade not in (
          'Estágio/Trainee', 'Júnior', 'Pleno', 'Sênior', 'Especialista',
          'Coordenador', 'Liderança', 'Diretoria', 'Técnico'
      )
    group by senioridade
)
select * from valores_invalidos

union all

-- raw_job_id deve ser único
select
    'raw_job_id_duplicado' as erro,
    count(*) as n
from (
    select raw_job_id, count(*) as n
    from {{ ref('int_jobs_normalized') }}
    group by raw_job_id
    having count(*) > 1
) dup
