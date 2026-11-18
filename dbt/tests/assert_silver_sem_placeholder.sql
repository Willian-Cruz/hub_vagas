{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Invariante de contrato NULL: campo sem informacao nunca vira o texto '
                      '"Nao informado"/"Confidencial" na Silver.'
    }
  )
}}
-- Contrato de NULL: campo sem informacao nunca vira o texto "Não informado"
select raw_job_id, origem
from {{ ref('jobs') }}
where lower(coalesce(empresa, '')) in ('não informado', 'nao informado', 'confidencial')
   or lower(coalesce(senioridade, '')) in ('não informado', 'nao informado')
   or lower(coalesce(localizacao, '')) in ('não informado', 'nao informado', 'localização não informada')
   or lower(coalesce(salario_texto, '')) in ('não informado', 'nao informado')
   or lower(coalesce(descricao, '')) in ('não informado', 'nao informado')
