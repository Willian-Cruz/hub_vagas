{{
  config(
    severity = 'warn',
    meta = {
      'documentacao': 'Verifica que a Catho está entregando dados para o Silver. '
                      'Se estiver vazia, o scraper ou o parser precisa de recalibração.'
    }
  )
}}

-- Catho é uma fonte ativa: deve haver vagas canônicas no Silver.
select count(*) as vagas_catho_silver
from {{ ref('jobs') }}
where origem = 'Catho'
  and is_canonical = true
