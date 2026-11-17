{# Silver: todas as linhas são mantidas (ninguém é apagado), com marcação de dedup.
   Campo sem informação é NULL (nunca "Não informado"). #}
with source_rows as (
    select * from {{ ref('stg_vagas_com_jobs') }}
    union all
    select * from {{ ref('stg_infojobs_jobs') }}
    union all
    select * from {{ ref('stg_gupy_jobs') }}
    union all
    select * from {{ ref('stg_catho_jobs') }}
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
        data_coleta,
        is_relevant
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
        data_coleta,
        is_relevant,
        -- Descrição truncada: termina em "..." ou é curta demais para ser confiável
        case
            when descricao is not null
                 and (descricao like '%...' or length(descricao) <= 160)
            then true
            else false
        end as descricao_truncada
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
        case
            when {{ normalize_modality('modalidade_raw') }} is not null then 'portal'
            when localizacao in ('Remoto', 'Híbrido') then 'local'
            else null
        end as modalidade_origem,
        -- Mesma vaga republicada com outro ID: título + empresa + local.
        case
            when empresa is not null or localizacao is not null
                then origem
                    || '|' || {{ fold_text('titulo') }}
                    || '|' || coalesce({{ fold_text('empresa') }}, '__SEM_EMPRESA__')
                    || '|' || coalesce({{ fold_text('localizacao') }}, '__SEM_LOCAL__')
        end as chave_conteudo,
        coalesce(id_externo, link) as chave_portal
    from normalized
),

-- Cada linha recebe um grupo de dedup (chave de conteúdo, cross-portal, ou a própria
-- chave do portal quando não há conteúdo). A linha mais recente do grupo é a canônica.
dedup_groups as (
    select
        *,
        coalesce(chave_conteudo, origem || '|' || chave_portal) as dedup_group_id,
        min(data_coleta) over (
            partition by coalesce(chave_conteudo, origem || '|' || chave_portal)
        ) as first_seen_at,
        max(data_coleta) over (
            partition by coalesce(chave_conteudo, origem || '|' || chave_portal)
        ) as last_seen_at,
        row_number() over (
            partition by coalesce(chave_conteudo, origem || '|' || chave_portal)
            order by data_coleta desc, data_publicacao desc nulls last, raw_job_id desc
        ) as content_rank
    from keyed
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
    data_coleta,
    dedup_group_id,
    first_seen_at,
    last_seen_at,
    is_relevant,
    descricao_truncada,
    modalidade_origem,
    (content_rank = 1) as is_canonical
from dedup_groups
