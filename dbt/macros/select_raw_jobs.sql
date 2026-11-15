{% macro select_raw_jobs(source_name) %}
select
    id as raw_job_id,
    origem,
    link,
    titulo,
    empresa,
    senioridade,
    localizacao,
    descricao,
    salario,
    data_coleta,
    id_externo,
    data_publicacao,
    modalidade,
    experiencia,
    escolaridade,
    qtd_posicoes,
    chave_conteudo
from {{ source('raw', 'jobs') }}
where lower(origem) = lower('{{ source_name }}')
{% endmacro %}
