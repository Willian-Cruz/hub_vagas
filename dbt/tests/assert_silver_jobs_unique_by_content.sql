{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Invariante de unicidade: a mesma vaga republicada com outro ID '
                      '(mesmo conteudo) deve contar uma vez na Silver.'
    }
  )
}}
-- A mesma vaga republicada com outro ID (mesmo título, empresa e local) conta uma vez
select chave_conteudo, count(*) as registros
from {{ ref('jobs') }}
where chave_conteudo is not null
group by chave_conteudo
having count(*) > 1
