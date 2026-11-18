{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Contrato Python<->dbt: raw.job_observations deve ter as '
                      'colunas de metadados que o Python grava '
                      '(JobRepository.salvar) e que o dbt staging usa para rastrear '
                      'execucoes. Falha se alguma coluna esperada estiver ausente.'
    }
  )
}}

-- Colunas obrigatórias em raw.job_observations (contrato Python -> dbt).
-- Retorna as colunas esperadas que ESTAO AUSENTES (falha se houver resultado).
with esperado as (
    select unnest(array[
        'run_id', 'source', 'source_job_id', 'collected_at',
        'link', 'payload_hash', 'raw_payload', 'is_relevant'
    ]) as column_name
),
presente as (
    select column_name
    from information_schema.columns
    where table_schema = 'raw'
      and table_name = 'job_observations'
)
select e.column_name as coluna_ausente
from esperado e
left join presente p
    on e.column_name = p.column_name
where p.column_name is null
