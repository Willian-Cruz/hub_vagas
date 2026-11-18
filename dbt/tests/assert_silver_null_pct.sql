{{
  config(
    severity = 'warn',
    meta = {
      'documentacao': 'Metrica de qualidade (soft): percentual de NULL por campo. '
                      'Limiares ajustaveis via `vars` em dbt_project.yml. '
                      'Limitacao conhecida: modalidade e salario apresentam NULL alto '
                      'porque Catho/Vagas.com nao trazem esses campos no card (não falham o build).'
    }
  )
}}

-- Data quality: verifica percentual de NULL em campos-chave da Silver.
--
-- Os limiares vêm de `vars` em dbt_project.yml (null_pct_*), para poderem ser
-- ajustados sem tocar no SQL. Valores "significativos": apertados o suficiente
-- para flagar regressões, mas folgados para aceitar portais que não trazem
-- certo campo (ex.: Catho não traz descricao/modalidade/salario no card).
--
-- Retorna uma linha por campo cujo percentual de NULL excede o limiar.
with stats as (
    select
        count(*) as total,
        sum(case when empresa is null then 1 else 0 end) as empresa_null,
        sum(case when localizacao is null then 1 else 0 end) as localizacao_null,
        sum(case when senioridade is null then 1 else 0 end) as senioridade_null,
        sum(case when modalidade is null then 1 else 0 end) as modalidade_null,
        sum(case when salario_texto is null then 1 else 0 end) as salario_null,
        sum(case when descricao is null then 1 else 0 end) as descricao_null
    from {{ ref('jobs') }}
)
select
    'empresa' as campo,
    empresa_null,
    total,
    round(100.0 * empresa_null / nullif(total, 0), 1) as pct_null,
    round(100.0 * {{ var('null_pct_empresa', 0.50) }}, 1) as limite_pct
from stats
where empresa_null > total * {{ var('null_pct_empresa', 0.50) }}

union all

select
    'localizacao' as campo,
    localizacao_null,
    total,
    round(100.0 * localizacao_null / nullif(total, 0), 1) as pct_null,
    round(100.0 * {{ var('null_pct_localizacao', 0.50) }}, 1) as limite_pct
from stats
where localizacao_null > total * {{ var('null_pct_localizacao', 0.50) }}

union all

select
    'senioridade' as campo,
    senioridade_null,
    total,
    round(100.0 * senioridade_null / nullif(total, 0), 1) as pct_null,
    round(100.0 * {{ var('null_pct_senioridade', 0.30) }}, 1) as limite_pct
from stats
where senioridade_null > total * {{ var('null_pct_senioridade', 0.30) }}

union all

select
    'modalidade' as campo,
    modalidade_null,
    total,
    round(100.0 * modalidade_null / nullif(total, 0), 1) as pct_null,
    round(100.0 * {{ var('null_pct_modalidade', 0.50) }}, 1) as limite_pct
from stats
where modalidade_null > total * {{ var('null_pct_modalidade', 0.50) }}

union all

select
    'salario_texto' as campo,
    salario_null,
    total,
    round(100.0 * salario_null / nullif(total, 0), 1) as pct_null,
    round(100.0 * {{ var('null_pct_salario', 0.40) }}, 1) as limite_pct
from stats
where salario_null > total * {{ var('null_pct_salario', 0.40) }}

union all

select
    'descricao' as campo,
    descricao_null,
    total,
    round(100.0 * descricao_null / nullif(total, 0), 1) as pct_null,
    round(100.0 * {{ var('null_pct_descricao', 0.30) }}, 1) as limite_pct
from stats
where descricao_null > total * {{ var('null_pct_descricao', 0.30) }}
