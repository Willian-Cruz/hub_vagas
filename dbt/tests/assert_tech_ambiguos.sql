-- Data quality: tecnologias ambíguas/curtas ("R", "Go") não devem ser
-- monitoradas porque geram falsos positivos (ex.: "R$" de salário, "Go" em
-- português). Se alguém adicioná-las à lista monitorada, este teste falha.
select tecnologia
from {{ ref('mart_demanda_tecnologias') }}
where lower(tecnologia) in ('r', 'go')
