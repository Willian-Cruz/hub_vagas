-- Gold: mart_vagas — Vagas Silver enriquecidas com tecnologias, prontas para exportação.
--
-- A lista de tecnologias vem da seed dbt/seeds/tecnologias_monitoradas.csv
-- (fonte única, compartilhada com o Python via tech_service.TECNOLOGIAS).
-- Só inclui as linhas canônicas (is_canonical = true) para não contar duplicatas.
with tecnologias as (
    select tecnologia from {{ ref('tecnologias_monitoradas') }}
),
mentions as (
    select
        jobs.origem,
        jobs.link as source_job_id,
        tecnologias.tecnologia
    from {{ ref('jobs') }} as jobs
    cross join tecnologias
    where (coalesce(jobs.descricao, '') || ' ' || coalesce(jobs.titulo, '')) ~* ('\m' || tecnologias.tecnologia || '\M')
)

select
    jobs.raw_job_id as id,
    jobs.titulo,
    jobs.empresa,
    jobs.senioridade,
    jobs.localizacao,
    jobs.salario_texto,
    jobs.modalidade,
    jobs.experiencia,
    jobs.escolaridade,
    jobs.qtd_posicoes,
    jobs.origem,
    jobs.id_externo,
    jobs.link,
    jobs.descricao,
    jobs.data_publicacao,
    jobs.data_coleta,
    jobs.descricao_truncada,
    coalesce(
        string_agg(distinct mentions.tecnologia, ', ' order by mentions.tecnologia),
        ''
    ) as tecnologias
from {{ ref('jobs') }} as jobs
left join mentions
    on mentions.origem = jobs.origem
   and mentions.source_job_id = jobs.link
where jobs.is_canonical
group by
    jobs.raw_job_id,
    jobs.titulo,
    jobs.empresa,
    jobs.senioridade,
    jobs.localizacao,
    jobs.salario_texto,
    jobs.modalidade,
    jobs.experiencia,
    jobs.escolaridade,
    jobs.qtd_posicoes,
    jobs.origem,
    jobs.id_externo,
    jobs.link,
    jobs.descricao,
    jobs.data_publicacao,
    jobs.data_coleta,
    jobs.descricao_truncada
