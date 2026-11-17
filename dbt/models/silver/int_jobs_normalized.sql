{# Camada Silver, etapa 2 de 3: normalização de campos (senioridade, localização,
   salário, modalidade) a partir da união. Nenhuma linha é descartada aqui. #}
with cleaned as (
    select * from {{ ref('int_jobs_unioned') }}
),

normalized as (
    select
        raw_job_id,
        origem,
        link,
        id_externo,
        titulo,
        empresa,
        -- Nível do portal tem prioridade; sem ele, infere do título; por fim, cascata completa
        {% set np = normalize_seniority('senioridade_raw') %}
        {% set tt = normalize_seniority('titulo', include_tecnico=false) %}
        {% set cascade = classify_seniority_cascade('senioridade_raw', 'titulo', 'experiencia', 'descricao') %}
        coalesce(
            {{ np }},
            {{ tt }},
            {{ cascade }}
        ) as senioridade,
        {{ normalize_location('localizacao_raw') }} as localizacao,
        descricao,
        {{ extract_salary('salario_raw', 'descricao') }} as salario,
        modalidade_raw,
        experiencia,
        escolaridade,
        data_publicacao,
        qtd_posicoes,
        data_coleta,
        is_relevant,
        descricao_truncada
    from cleaned
)

select * from normalized
