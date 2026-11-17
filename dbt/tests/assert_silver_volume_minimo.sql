-- Data quality: garante volume mínimo de vagas na Silver quando há dados.
-- Falha apenas se há vagas (count > 0) mas abaixo do threshold mínimo (10).
-- Não falha quando a tabela está vazia (ainda não houve coleta).
select count(*) as total_vagas
from {{ ref('jobs') }}
having count(*) > 0 and count(*) < 10
