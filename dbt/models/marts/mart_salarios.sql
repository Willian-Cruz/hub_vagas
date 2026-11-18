-- Gold: mart_salarios — cobertura salarial por origem e senioridade.
--
-- Denominador = total de vagas; numerador = vagas com salário informado.
-- `a_combinar` só aparece quando o portal informa explicitamente (não é fallback).
select
    origem,
    senioridade,
    count(*) as total_vagas,
    sum(case when salario_tipo in ('exato', 'faixa') then 1 else 0 end) as n_com_salario,
    round(
        100.0 * sum(case when salario_tipo in ('exato', 'faixa') then 1 else 0 end)
        / nullif(count(*), 0),
        1
    ) as pct_com_salario,
    round(avg(salario_min), 2) as salario_min_medio,
    round(avg(salario_max), 2) as salario_max_medio,
    round(percentile_cont(0.5) within group (order by salario_min)::numeric, 2) as salario_min_mediana,
    round(percentile_cont(0.5) within group (order by salario_max)::numeric, 2) as salario_max_mediana,
    current_timestamp as atualizado_em
from {{ ref('jobs') }}
where senioridade is not null
group by origem, senioridade
