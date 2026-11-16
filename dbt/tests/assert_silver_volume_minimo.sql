-- Data quality: garante volume mínimo de vagas na Silver
-- Ajuste o threshold conforme esperado no ambiente
select count(*) as total_vagas
from {{ ref('jobs') }}
having count(*) < 10