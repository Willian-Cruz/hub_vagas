select
    (collected_at at time zone 'America/Sao_Paulo')::date as data_coleta,
    source as origem,
    count(*) as observacoes,
    count(distinct source_job_id) as vagas_distintas
from {{ source('bronze', 'job_observations') }}
group by (collected_at at time zone 'America/Sao_Paulo')::date, source
