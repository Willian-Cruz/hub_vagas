select
    origem,
    localizacao,
    senioridade,
    count(*) as vagas_no_snapshot,
    count(distinct empresa) as empresas,
    max(data_coleta) as atualizado_em
from {{ ref('jobs') }}
group by origem, localizacao, senioridade
