{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'first_seen_at nao pode ser posterior a last_seen_at.'
    }
  )
}}

-- A primeira observacao de um grupo nao pode ser posterior à última.
select *
from {{ ref('jobs') }}
where first_seen_at > last_seen_at
