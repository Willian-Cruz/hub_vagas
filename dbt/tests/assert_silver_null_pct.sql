-- Data quality: verifica percentual de NULL em campos-chave
-- Se mais de 50% dos registros têm empresa NULL, algo está errado na extração
with stats as (
    select
        count(*) as total,
        sum(case when empresa is null then 1 else 0 end) as empresa_null,
        sum(case when localizacao is null then 1 else 0 end) as localizacao_null,
        sum(case when senioridade is null then 1 else 0 end) as senioridade_null,
        sum(case when modalidade is null then 1 else 0 end) as modalidade_null,
        sum(case when salario is null then 1 else 0 end) as salario_null,
        sum(case when descricao is null then 1 else 0 end) as descricao_null
    from {{ ref('jobs') }}
)
select
    'empresa' as campo,
    empresa_null,
    total,
    round(100.0 * empresa_null / nullif(total, 0), 1) as pct_null
from stats
where empresa_null > total * 0.5

union all

select
    'localizacao' as campo,
    localizacao_null,
    total,
    round(100.0 * localizacao_null / nullif(total, 0), 1) as pct_null
from stats
where localizacao_null > total * 0.5

union all

select
    'senioridade' as campo,
    senioridade_null,
    total,
    round(100.0 * senioridade_null / nullif(total, 0), 1) as pct_null
from stats
where senioridade_null > total * 0.5

union all

select
    'modalidade' as campo,
    modalidade_null,
    total,
    round(100.0 * modalidade_null / nullif(total, 0), 1) as pct_null
from stats
where modalidade_null > total * 0.5

union all

select
    'salario' as campo,
    salario_null,
    total,
    round(100.0 * salario_null / nullif(total, 0), 1) as pct_null
from stats
where salario_null > total * 0.9  -- salário costuma ser mais esparso

union all

select
    'descricao' as campo,
    descricao_null,
    total,
    round(100.0 * descricao_null / nullif(total, 0), 1) as pct_null
from stats
where descricao_null > total * 0.5