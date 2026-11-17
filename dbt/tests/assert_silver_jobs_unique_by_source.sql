{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Invariante de unicidade: nao pode haver a mesma origem+link duplicada na Silver.'
    }
  )
}}
select origem, link, count(*) as registros
from {{ ref('jobs') }}
group by origem, link
having count(*) > 1
