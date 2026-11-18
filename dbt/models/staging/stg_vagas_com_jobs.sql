{{ config(materialized='view') }}

-- Staging Vagas.com: lê da tabela append-only `raw.job_observations` (P3).
-- Cada fonte pode ter várias observações da mesma vaga; mantém a mais recente.
with observacoes as (
    select
        id as raw_job_id,
        source as origem,
        source_job_id as id_externo,
        collected_at as data_coleta,
        is_relevant,
        raw_payload->>'link' as link,
        raw_payload->>'titulo' as titulo,
        raw_payload->>'empresa' as empresa,
        raw_payload->>'senioridade' as senioridade,
        raw_payload->>'localizacao' as localizacao,
        raw_payload->>'descricao' as descricao,
        raw_payload->>'salario' as salario,
        raw_payload->>'modalidade' as modalidade,
        raw_payload->>'experiencia' as experiencia,
        raw_payload->>'escolaridade' as escolaridade,
        nullif(raw_payload->>'qtd_posicoes', '')::integer as qtd_posicoes,
        (raw_payload->>'data_publicacao')::timestamptz as data_publicacao,
        nullif(raw_payload->>'data_atualizacao', '')::timestamptz as data_atualizacao
    from {{ source('raw_observations', 'job_observations') }}
    where lower(source) = lower('Vagas.com')
),
ranked as (
    select
        *,
        row_number() over (
            partition by coalesce(id_externo, link)
            order by data_coleta desc, raw_job_id desc
        ) as rn
    from observacoes
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
    data_coleta,
    data_publicacao,
    data_atualizacao,
    modalidade,
    experiencia,
    escolaridade,
    qtd_posicoes,
    is_relevant
from ranked
where rn = 1
