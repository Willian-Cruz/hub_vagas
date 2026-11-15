select origem, link, count(*) as registros
from {{ ref('jobs') }}
group by origem, link
having count(*) > 1
