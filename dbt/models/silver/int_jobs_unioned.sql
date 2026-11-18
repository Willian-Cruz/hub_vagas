{# Camada Silver, etapa 1 de 3: união das 4 fontes de staging + limpeza básica.
   Nenhuma linha é descartada aqui (apenas linhas sem título/link são descartadas). #}
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
        data_atualizacao,
        is_relevant,
        -- Descrição truncada: termina em "..." ou é curta demais para ser confiável
        case
            when descricao is not null
                 and (descricao like '%...' or length(descricao) <= 160)
            then true
            else false
        end as descricao_truncada
    from source_rows
    -- Sem título e sem link a vaga não é utilizável
    where titulo is not null
      and link is not null
)

select * from cleaned
