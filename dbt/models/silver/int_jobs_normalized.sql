{# Camada Silver, etapa 2 de 3: normalização de campos (senioridade, localização,
   salário, modalidade) a partir da união. Nenhuma linha é descartada aqui. #}
with cleaned as (
    select * from {{ ref('int_jobs_unioned') }}
),
salario_texto as (
    select
        *,
        {{ extract_salary('salario_raw', 'descricao') }} as salario_texto
    from cleaned
)
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
    -- senioridade_inferida: true quando não veio do campo do portal (senioridade_raw é NULL)
    (senioridade_raw is null) as senioridade_inferida,
    {{ normalize_location('localizacao_raw') }} as localizacao,
    descricao,
    -- Salário: texto como publicado + componentes numéricos e tipo
    salario_texto,
    {{ salario_min('salario_texto') }} as salario_min,
    {{ salario_max('salario_texto') }} as salario_max,
    {{ salario_tipo('salario_texto') }} as salario_tipo,
    -- salario_inferido: true quando não veio do campo do portal (salario_raw é NULL)
    (salario_raw is null) as salario_inferido,
    modalidade_raw,
    experiencia,
    escolaridade,
    data_publicacao,
    qtd_posicoes,
    data_coleta,
    ingested_at,
    scraper_version,
    run_id,
    data_atualizacao,
    is_relevant,
    descricao_truncada
from salario_texto
