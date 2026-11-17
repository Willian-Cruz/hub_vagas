-- Gold: mart_salarios — cobertura salarial por origem.
--
-- Denominador = total de vagas; numerador = vagas com salário informado.
-- Alinha-se à decisão P4: `a_combinar` só quando o portal informa explicitamente.
select
    origem,
    count(*) as total_vagas,
    sum(case when salario is not null then 1 else 0 end) as vagas_com_salario,
    round(
        100.0 * sum(case when salario is not null then 1 else 0 end)
        / nullif(count(*), 0),
        1
    ) as pct_com_salario,
    sum(case when salario is not null then 1 else 0 end)
        * 1.0 / nullif(count(*), 0) as share_com_salario,
    current_timestamp as atualizado_em
from {{ ref('jobs') }}
group by origem
