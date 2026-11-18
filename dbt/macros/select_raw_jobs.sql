{% macro select_raw_jobs(source_name) %}
select
    id as raw_job_id,
    source as origem,
    raw_payload->>'link' as link,
    raw_payload->>'titulo' as titulo,
    raw_payload->>'empresa' as empresa,
    raw_payload->>'senioridade' as senioridade,
    raw_payload->>'localizacao' as localizacao,
    raw_payload->>'descricao' as descricao,
    raw_payload->>'salario' as salario,
    collected_at as data_coleta,
    source_job_id as id_externo,
    (raw_payload->>'data_publicacao')::timestamptz as data_publicacao,
    raw_payload->>'modalidade' as modalidade,
    raw_payload->>'experiencia' as experiencia,
    raw_payload->>'escolaridade' as escolaridade,
    nullif(raw_payload->>'qtd_posicoes', '')::integer as qtd_posicoes,
    raw_payload->>'chave_conteudo' as chave_conteudo
from {{ source('raw_observations', 'job_observations') }}
where lower(source) = lower('{{ source_name }}')
{% endmacro %}
