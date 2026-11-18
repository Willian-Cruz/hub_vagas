-- Gold: mart_qualidade_campos — saúde do parser por fonte, dia e campo.
--
-- Para cada fonte (origem) e data de coleta, calcula o percentual de não-nulo
-- de cada campo-chave extraído pelo scraper. Isso permite detectar quando um
-- portal renomeia uma classe CSS e um campo passa a vir NULL em silêncio.
--
-- Lê da Silver ({{ ref('jobs') }}), que já teve NULL_IF placeholder aplicado.
-- Um campo que antes era preenchido e passa a ser NULL indica que o parser
-- daquele portal precisa de recalibração.
with campos as (
    select
        origem as fonte,
        (data_coleta at time zone 'America/Sao_Paulo')::date as data_coleta,
        'salario_texto' as campo,
        count(*) as total_vagas,
        sum(case when salario_texto is not null then 1 else 0 end) as vagas_nao_nulas
    from {{ ref('jobs') }}
    group by origem, (data_coleta at time zone 'America/Sao_Paulo')::date

    union all

    select
        origem as fonte,
        (data_coleta at time zone 'America/Sao_Paulo')::date,
        'empresa',
        count(*),
        sum(case when empresa is not null then 1 else 0 end)
    from {{ ref('jobs') }}
    group by origem, (data_coleta at time zone 'America/Sao_Paulo')::date

    union all

    select
        origem as fonte,
        (data_coleta at time zone 'America/Sao_Paulo')::date,
        'modalidade',
        count(*),
        sum(case when modalidade is not null then 1 else 0 end)
    from {{ ref('jobs') }}
    group by origem, (data_coleta at time zone 'America/Sao_Paulo')::date

    union all

    select
        origem as fonte,
        (data_coleta at time zone 'America/Sao_Paulo')::date,
        'senioridade',
        count(*),
        sum(case when senioridade is not null then 1 else 0 end)
    from {{ ref('jobs') }}
    group by origem, (data_coleta at time zone 'America/Sao_Paulo')::date

    union all

    select
        origem as fonte,
        (data_coleta at time zone 'America/Sao_Paulo')::date,
        'descricao',
        count(*),
        sum(case when descricao is not null then 1 else 0 end)
    from {{ ref('jobs') }}
    group by origem, (data_coleta at time zone 'America/Sao_Paulo')::date

    union all

    select
        origem as fonte,
        (data_coleta at time zone 'America/Sao_Paulo')::date,
        'localizacao',
        count(*),
        sum(case when localizacao is not null then 1 else 0 end)
    from {{ ref('jobs') }}
    group by origem, (data_coleta at time zone 'America/Sao_Paulo')::date
)
select
    fonte,
    data_coleta,
    campo,
    total_vagas,
    vagas_nao_nulas,
    round(100.0 * vagas_nao_nulas::numeric / nullif(total_vagas, 0), 1) as pct_nao_nulo,
    current_timestamp as atualizado_em
from campos
order by fonte, data_coleta, campo
