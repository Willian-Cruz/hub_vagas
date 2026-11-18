{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Detecta mudanças incompatíveis no contrato Python<->dbt: '
                      'se o tipo de alguma coluna obrigatória de raw.job_observations '
                      'mudar, o teste falha. Mudanças incompatíveis devem ser '
                      'detectadas antes de contaminar os modelos analíticos.'
    }
  )
}}

-- Verifica que os tipos das colunas obrigatórias não mudaram.
-- Se algum tipo mudar, o teste retorna linhas e falha.
with esperado as (
    select *
    from (values
        ('id', 'bigint'),
        ('run_id', 'uuid'),
        ('source', 'text'),
        ('source_job_id', 'text'),
        ('collected_at', 'timestamp with time zone'),
        ('ingested_at', 'timestamp with time zone'),
        ('scraper_version', 'text'),
        ('payload_hash', 'text'),
        ('raw_payload', 'jsonb'),
        ('is_relevant', 'boolean'),
        ('created_at', 'timestamp with time zone')
    ) as t(column_name, expected_type)
),
presente as (
    select column_name, data_type
    from information_schema.columns
    where table_schema = 'raw'
      and table_name = 'job_observations'
)
select
    e.column_name,
    e.expected_type,
    p.data_type as tipo_atual
from esperado e
left join presente p
    on e.column_name = p.column_name
where p.column_name is null
   or p.data_type <> e.expected_type
