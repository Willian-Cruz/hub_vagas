{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'dias_no_ar nao pode ser negativo.'
    }
  )
}}

-- dias_no_ar é (last_seen_at - first_seen_at) em dias; nunca negativo.
select *
from {{ ref('jobs') }}
where dias_no_ar is not null
  and dias_no_ar < 0
