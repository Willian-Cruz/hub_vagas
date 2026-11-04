{% macro select_bronze_jobs(source_name) %}
select
    id as bronze_observation_id,
    run_id::text as run_id,
    source as origem,
    source_job_id,
    collected_at,
    payload_hash,
    nullif(trim(raw_payload -> 'job' ->> 'titulo'), '') as titulo,
    nullif(trim(raw_payload -> 'job' ->> 'empresa'), '') as empresa,
    nullif(trim(raw_payload -> 'job' ->> 'senioridade'), '') as senioridade,
    nullif(trim(raw_payload -> 'job' ->> 'localizacao'), '') as localizacao,
    nullif(trim(raw_payload -> 'job' ->> 'descricao'), '') as descricao,
    nullif(trim(raw_payload -> 'job' ->> 'salario'), '') as salario,
    nullif(trim(raw_payload -> 'job' ->> 'link'), '') as link
from {{ source('bronze', 'job_observations') }}
where lower(source) = lower('{{ source_name }}')
{% endmacro %}
