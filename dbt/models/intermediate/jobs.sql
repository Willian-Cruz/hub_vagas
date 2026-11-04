with source_rows as (
    select * from {{ ref('stg_vagas_com_jobs') }}
    union all
    select * from {{ ref('stg_infojobs_jobs') }}
    union all
    select * from {{ ref('stg_gupy_jobs') }}
),

raw_fields as (
    select
        *,
        case
            when lower(trim(coalesce(senioridade, ''))) in ('', 'não informado', 'nao informado')
                then null
            else trim(senioridade)
        end as senioridade_raw,
        case
            when lower(trim(coalesce(localizacao, ''))) in ('', 'não informado', 'nao informado')
                then null
            else trim(localizacao)
        end as localizacao_raw,
        case
            when lower(trim(coalesce(salario, ''))) in ('', 'não informado', 'nao informado')
                then null
            else trim(salario)
        end as salario_raw
    from source_rows
),

cleaned as (
    select
        bronze_observation_id,
        run_id,
        origem,
        coalesce(nullif(trim(source_job_id), ''), nullif(trim(link), '')) as source_job_id,
        coalesce(nullif(trim(link), ''), nullif(trim(source_job_id), '')) as link,
        coalesce(nullif(trim(titulo), ''), 'Não informado') as titulo,
        coalesce(nullif(trim(empresa), ''), 'Não informado') as empresa,
        {{ normalize_seniority('senioridade_raw') }} as senioridade,
        {{ normalize_location('localizacao_raw') }} as localizacao,
        coalesce(nullif(trim(descricao), ''), 'Não informado') as descricao,
        {{ extract_salary('salario_raw', 'descricao') }} as salario,
        collected_at as data_coleta,
        payload_hash
    from raw_fields
    where coalesce(nullif(trim(link), ''), nullif(trim(source_job_id), '')) is not null
),

ranked as (
    select
        *,
        row_number() over (
            partition by origem, source_job_id
            order by data_coleta desc, bronze_observation_id desc
        ) as observation_rank
    from cleaned
)

select
    bronze_observation_id,
    run_id,
    origem,
    source_job_id,
    link,
    titulo,
    empresa,
    senioridade,
    localizacao,
    descricao,
    salario,
    data_coleta,
    payload_hash
from ranked
where observation_rank = 1
