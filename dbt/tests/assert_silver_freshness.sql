-- Data quality: verifica se os dados da Silver são recentes
-- Alerta se a última coleta foi há mais de 48 horas
with ultima_coleta as (
    select max(data_coleta) as ultima
    from {{ ref('jobs') }}
)
select
    ultima as ultima_coleta,
    current_timestamp as agora,
    extract(epoch from (current_timestamp - ultima)) / 3600 as horas_desde_coleta
from ultima_coleta
where ultima < current_timestamp - interval '48 hours'