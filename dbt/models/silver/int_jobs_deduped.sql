{# Camada Silver, etapa 3 de 3: deduplicação por grupo de conteúdo (cross-portal).
   Todas as linhas são mantidas (ninguém é apagado); apenas é marcada a linha
   canônica de cada grupo (is_canonical = true). #}
with normalized as (
    select * from {{ ref('int_jobs_normalized') }}
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
    salario_texto,
    salario_min,
    salario_max,
    salario_tipo,
    modalidade,
    experiencia,
    escolaridade,
    qtd_posicoes,
    data_publicacao,
    -- Precisão da data de publicação: hora (tem componente de hora), dia (apenas data),
    -- estimada (veio de texto relativo, ex: "Há 7 dias"). Calculada a partir do
    -- timestamp; o scraper pode sobrescrever com 'estimada' quando souber.
    case
        when data_publicacao is null then null
        when extract(hour from data_publicacao) > 0
             or extract(minute from data_publicacao) > 0
             or extract(second from data_publicacao) > 0 then 'hora'
        else 'dia'
    end as data_publicacao_precisao,
    chave_conteudo,
    data_coleta,
    dedup_group_id,
    first_seen_at,
    last_seen_at,
    is_relevant,
    descricao_truncada,
    modalidade_origem,
    (content_rank = 1) as is_canonical,
    -- Dias que a vaga ficou no ar: diferença entre primeira e última coleta
    -- do mesmo grupo de dedup. NULL quando só há uma observação.
    case
        when first_seen_at is distinct from last_seen_at
        then extract(epoch from (last_seen_at - first_seen_at)) / 86400
        else null
    end as dias_no_ar,
    -- Vaga ativa: vista nos últimos 3 dias (janela configurável)
    case
        when last_seen_at >= (select max(data_coleta) from {{ ref('int_jobs_unioned') }}) - interval '3 days'
        then true
        else false
    end as is_ativa
from dedup_groups
