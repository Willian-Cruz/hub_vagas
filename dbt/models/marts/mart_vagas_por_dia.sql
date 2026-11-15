select
    (data_coleta at time zone 'America/Sao_Paulo')::date as data_coleta,
    origem as source,
    count(*) as observacoes,
    count(distinct link) as vagas_distintas
from {{ source('raw', 'jobs') }}
group by (data_coleta at time zone 'America/Sao_Paulo')::date, origem
