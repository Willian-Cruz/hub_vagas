-- A mesma vaga republicada com outro ID (mesmo título, empresa e local) conta uma vez
select chave_conteudo, count(*) as registros
from {{ ref('jobs') }}
where chave_conteudo is not null
group by chave_conteudo
having count(*) > 1
