-- Contrato de NULL: campo sem informação nunca vira o texto "Não informado"
select bronze_observation_id, origem
from {{ ref('jobs') }}
where lower(coalesce(empresa, '')) in ('não informado', 'nao informado', 'confidencial')
   or lower(coalesce(senioridade, '')) in ('não informado', 'nao informado')
   or lower(coalesce(localizacao, '')) in ('não informado', 'nao informado', 'localização não informada')
   or lower(coalesce(salario, '')) in ('não informado', 'nao informado')
   or lower(coalesce(descricao, '')) in ('não informado', 'nao informado')
