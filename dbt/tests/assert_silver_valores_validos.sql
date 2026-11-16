-- Data quality: valida valores permitidos em campos categóricos
with invalidos as (
    select
        raw_job_id,
        origem,
        'senioridade' as campo,
        senioridade as valor
    from {{ ref('jobs') }}
    where senioridade is not null
      and senioridade not in ('Júnior', 'Pleno', 'Sênior', 'Especialista', 'Coordenador', 'Liderança', 'Diretoria', 'Estágio/Trainee', 'Técnico')

    union all

    select
        raw_job_id,
        origem,
        'modalidade' as campo,
        modalidade as valor
    from {{ ref('jobs') }}
    where modalidade is not null
      and modalidade not in ('Presencial', 'Híbrido', 'Remoto')

    union all

    select
        raw_job_id,
        origem,
        'localizacao' as campo,
        localizacao as valor
    from {{ ref('jobs') }}
    where localizacao is not null
      and localizacao = 'Híbrido'  -- 'Híbrido' deve ser normalizado para modalidade, não localização
      and localizacao not like '% - %'  -- formato cidade - UF

    union all

    select
        raw_job_id,
        origem,
        'empresa' as campo,
        empresa as valor
    from {{ ref('jobs') }}
    where empresa is not null
      and lower(empresa) in ('confidencial', 'não informado', 'nao informado')
)
select * from invalidos