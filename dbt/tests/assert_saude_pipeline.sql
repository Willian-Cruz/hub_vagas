{{
  config(
    severity = 'warn',
    meta = {
      'documentacao': 'Verifica que o mart_saude_pipeline tem dados para todas as '
                      'fontes ativas e que nenhuma fonte está em estado crítico '
                      'sem coleta de sucesso há mais de 72h.'
    }
  )
}}

-- Cada fonte ativa deve ter pelo menos uma execução registrada.
-- Fontes com status_saude = 'sem_coleta_sucesso' ou 'dados_desatualizados'
-- são reportadas como warning (não error, pois podem ser fontes novas).
with fontes_sem_sucesso as (
    select *
    from {{ ref('mart_saude_pipeline') }}
    where status_saude in ('sem_coleta_sucesso', 'dados_desatualizados')
)
select
    origem,
    status_saude,
    ultima_coleta_sucesso,
    ultimo_erro
from fontes_sem_sucesso
