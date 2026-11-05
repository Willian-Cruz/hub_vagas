select distinct on (source)
    source as origem,
    status,
    pages_processed as paginas_processadas,
    jobs_found as vagas_encontradas,
    error as erro,
    started_at as iniciado_em,
    finished_at as finalizado_em
from {{ source('bronze', 'scrape_runs') }}
order by source, finished_at desc
