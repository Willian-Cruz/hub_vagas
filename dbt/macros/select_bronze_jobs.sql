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
    nullif(trim(raw_payload -> 'job' ->> 'link'), '') as link,
    {# Campos adicionados na revisão dos scrapers. Observações antigas não os têm: ficam NULL. #}
    nullif(trim(raw_payload -> 'job' ->> 'id_externo'), '') as id_externo,
    nullif(raw_payload -> 'job' ->> 'data_publicacao', '')::timestamp as data_publicacao,
    nullif(trim(raw_payload -> 'job' ->> 'modalidade'), '') as modalidade,
    nullif(trim(raw_payload -> 'job' ->> 'experiencia'), '') as experiencia,
    nullif(trim(raw_payload -> 'job' ->> 'escolaridade'), '') as escolaridade,
    nullif(raw_payload -> 'job' ->> 'qtd_posicoes', '')::integer as qtd_posicoes
from {{ source('bronze', 'job_observations') }}
where lower(source) = lower('{{ source_name }}')
{% endmacro %}
