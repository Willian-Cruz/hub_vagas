with tecnologias (tecnologia) as (
    {{ monitored_technologies() }}
),

mentions as (
    select
        jobs.origem,
        jobs.source_job_id,
        tecnologias.tecnologia
    from {{ ref('jobs') }} as jobs
    cross join tecnologias
    where coalesce(jobs.descricao, '') ~* ('\m' || tecnologias.tecnologia || '\M')
)

select
    jobs.bronze_observation_id as id,
    jobs.titulo,
    jobs.empresa,
    jobs.senioridade,
    jobs.localizacao,
    jobs.salario,
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
    coalesce(
        string_agg(distinct mentions.tecnologia, ', ' order by mentions.tecnologia),
        ''
    ) as tecnologias
from {{ ref('jobs') }} as jobs
left join mentions
    on mentions.origem = jobs.origem
   and mentions.source_job_id = jobs.source_job_id
group by
    jobs.bronze_observation_id,
    jobs.titulo,
    jobs.empresa,
    jobs.senioridade,
    jobs.localizacao,
    jobs.salario,
    jobs.modalidade,
    jobs.experiencia,
    jobs.escolaridade,
    jobs.qtd_posicoes,
    jobs.origem,
    jobs.id_externo,
    jobs.link,
    jobs.descricao,
    jobs.data_publicacao,
    jobs.data_coleta
