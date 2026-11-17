{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Invariante de unicidade: mesmo ID no portal nao pode aparecer duas vezes na Silver.'
    }
  )
}}
-- Mesmo ID no portal não pode aparecer duas vezes na Silver
select origem, id_externo, count(*) as registros
from {{ ref('jobs') }}
where id_externo is not null
group by origem, id_externo
having count(*) > 1
