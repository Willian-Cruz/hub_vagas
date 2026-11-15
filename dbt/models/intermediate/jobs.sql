{# Silver: uma vaga por portal e identificador, sem repetidas.
   Campo sem informação é NULL (nunca "Não informado"). #}
with source_rows as (
    select * from {{ ref('stg_vagas_com_jobs') }}
    union all
    select * from {{ ref('stg_infojobs_jobs') }}
    union all
    select * from {{ ref('stg_gupy_jobs') }}
),

cleaned as (
    select
        raw_job_id,
        origem,
        coalesce(nullif(trim(link), ''), nullif(trim(link), '')) as link,
        id_externo,
        {{ null_if_placeholder('titulo') }} as titulo,
        {{ null_if_placeholder('empresa') }} as empresa,
        {{ null_if_placeholder('senioridade') }} as senioridade_raw,
        {{ null_if_placeholder('localizacao') }} as localizacao_raw,
        {{ null_if_placeholder('descricao') }} as descricao,
        {{ null_if_placeholder('salario') }} as salario_raw,
        {{ null_if_placeholder('modalidade') }} as modalidade_raw,
        {{ null_if_placeholder('experiencia') }} as experiencia,
        {{ null_if_placeholder('escolaridade') }} as escolaridade,
        data_publicacao,
        qtd_posicoes,
        data_coleta
    from source_rows
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
        data_coleta
    from cleaned
    -- Sem título e sem link a vaga não é utilizável
    where titulo is not null
      and link is not null
),

keyed as (
    select
        *,
        coalesce(
            {{ normalize_modality('modalidade_raw') }},
            case when localizacao in ('Remoto', 'Híbrido') then localizacao end
        ) as modalidade,
        -- Mesma vaga republicada com outro ID: título + empresa + local.
        -- Sem empresa ou local a chave fica NULL (não junta vagas diferentes).
        case
            when empresa is not null and localizacao is not null
                then origem
                    || '|' || {{ fold_text('titulo') }}
                    || '|' || {{ fold_text('empresa') }}
                    || '|' || {{ fold_text('localizacao') }}
        end as chave_conteudo,
        coalesce(id_externo, link) as chave_portal
    from normalized
),

latest_per_portal_id as (
    select
        *,
        row_number() over (
            partition by origem, chave_portal
            order by data_coleta desc, raw_job_id desc
        ) as portal_rank
    from keyed
),

latest as (
    select * from latest_per_portal_id where portal_rank = 1
),

ranked as (
    select
        *,
        case
            when chave_conteudo is null then 1
            else row_number() over (
                partition by chave_conteudo
                order by data_coleta desc, data_publicacao desc nulls last, raw_job_id desc
            )
        end as content_rank
    from latest
)

select
    raw_job_id,
    origem,
    link,
    id_externo,
    titulo,
    empresa,
    senioridade,
    localizacao,
    descricao,
    salario,
    modalidade,
    experiencia,
    escolaridade,
    qtd_posicoes,
    data_publicacao,
    chave_conteudo,
    data_coleta
from ranked
where content_rank = 1
