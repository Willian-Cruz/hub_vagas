-- Gold: mart_saude_pipeline — visão consolidada da saúde do pipeline.
--
-- Reúne indicadores operacionais por fonte e execução para responder:
--   - Qual é o estado geral do pipeline?
-- - Qual fonte está falhando?
-- - Qual foi a última coleta bem-sucedida?
-- - Quanto tempo a coleta demorou?
-- - Quantas vagas foram processadas?
-- - Qual etapa apresentou falha?
-- - O volume coletado está fora do padrão?
-- - Os modelos analíticos estão atualizados?
-- - A qualidade dos dados está se degradando?
--
-- Lê de bronze.scrape_runs (execuções) e silver.jobs (volume por fonte).
-- Não depende de tabelas externas além dessas duas.

with execucoes as (
    select
        source as origem,
        count(*) as total_execucoes,
        count(*) filter (where status = 'SUCCESS') as sucessos,
        count(*) filter (where status = 'FAILED') as falhas,
        count(*) filter (where status = 'PARTIAL') as parciais,
        count(*) filter (where status = 'EMPTY') as vazias,
        max(finished_at) filter (where status = 'SUCCESS') as ultima_coleta_sucesso,
        max(finished_at) filter (where status in ('SUCCESS', 'PARTIAL')) as ultima_tentativa,
        max(started_at) as ultima_inicio,
        avg(extract(epoch from (finished_at - started_at))) as duracao_media_seg,
        max(extract(epoch from (finished_at - started_at))) as duracao_maxima_seg,
        sum(jobs_found) as total_vagas_coletadas,
        avg(jobs_found) as media_vagas_por_execucao,
        max(error) filter (where status = 'FAILED') as ultimo_erro
    from {{ source('bronze', 'scrape_runs') }}
    group by source
),
volume_silver as (
    select
        origem,
        count(*) as vagas_na_silver,
        count(*) filter (where is_canonical) as vagas_canonicas,
        count(*) filter (where is_ativa) as vagas_ativas,
        max(data_coleta) as ultima_coleta_silver
    from {{ ref('jobs') }}
    group by origem
),
saude as (
    select
        e.origem,
        e.total_execucoes,
        e.sucessos,
        e.falhas,
        e.parciais,
        e.vazias,
        round(100.0 * e.sucessos::numeric / nullif(e.total_execucoes, 0), 1) as pct_sucesso,
        round(100.0 * e.falhas::numeric / nullif(e.total_execucoes, 0), 1) as pct_falha,
        e.ultima_coleta_sucesso,
        e.ultima_tentativa,
        e.ultima_inicio,
        round(e.duracao_media_seg, 2) as duracao_media_seg,
        round(e.duracao_maxima_seg, 2) as duracao_maxima_seg,
        e.total_vagas_coletadas,
        round(e.media_vagas_por_execucao, 1) as media_vagas_por_execucao,
        v.vagas_na_silver,
        v.vagas_canonicas,
        v.vagas_ativas,
        v.ultima_coleta_silver,
        e.ultimo_erro,
        -- Status de saúde da fonte
        case
            when e.ultima_coleta_sucesso is null then 'sem_coleta_sucesso'
            when e.ultima_coleta_sucesso < now() - interval '72 hours' then 'dados_desatualizados'
            when e.falhas > 0 and e.sucessos = 0 then 'sempre_falha'
            when e.falhas > 0 then 'falhas_intermitentes'
            when round(100.0 * e.sucessos::numeric / nullif(e.total_execucoes, 0), 1) < 80 then 'baixa_confiabilidade'
            else 'saudavel'
        end as status_saude
    from execucoes e
    left join volume_silver v
        on e.origem = v.origem
    group by
        e.origem, e.total_execucoes, e.sucessos, e.falhas, e.parciais, e.vazias,
        e.ultima_coleta_sucesso, e.ultima_tentativa, e.ultima_inicio,
        e.duracao_media_seg, e.duracao_maxima_seg, e.total_vagas_coletadas,
        e.media_vagas_por_execucao, e.ultimo_erro,
        v.vagas_na_silver, v.vagas_canonicas,
        v.vagas_ativas, v.ultima_coleta_silver
)
select
    origem,
    total_execucoes,
    sucessos,
    falhas,
    parciais,
    vazias,
    pct_sucesso,
    pct_falha,
    ultima_coleta_sucesso,
    ultima_tentativa,
    ultima_inicio,
    duracao_media_seg,
    duracao_maxima_seg,
    total_vagas_coletadas,
    media_vagas_por_execucao,
    vagas_na_silver,
    vagas_canonicas,
    vagas_ativas,
    ultima_coleta_silver,
    status_saude,
    ultimo_erro,
    current_timestamp as atualizado_em
from saude
