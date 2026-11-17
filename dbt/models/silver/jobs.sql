{# Camada Silver: alias para a etapa final de dedup (int_jobs_deduped).
   Mantido para compatibilidade com testes e marts que fazem ref('jobs'). #}
select * from {{ ref('int_jobs_deduped') }}
