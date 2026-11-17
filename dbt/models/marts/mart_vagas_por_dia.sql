select
    (collected_at at time zone 'America/Sao_Paulo')::date as data_coleta,
    source as source,
    count(*) as observacoes,
    count(distinct raw_payload->>'link') as vagas_distintas
from {{ source('raw_observations', 'job_observations') }}
group by (collected_at at time zone 'America/Sao_Paulo')::date, source
