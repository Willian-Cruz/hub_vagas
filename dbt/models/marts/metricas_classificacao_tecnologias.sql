{{
  config(
    materialized = 'view',
    meta = {
      'documentacao': 'Metricas de precisao e recall da classificacao de tecnologias '
                      'por tecnologia avaliada. Usado para monitoramento, nao como teste de falha.'
    }
  )
}}

-- Conjunto de validacao rotulado para classificacao de tecnologias.
with exemplos as (
    select * from {{ ref('classificacao_tecnologias_validacao') }}
),
tecnologias as (
    select tecnologia from {{ ref('tecnologias_monitoradas') }}
),
-- Aplica o mesmo regex usado nos marts: word boundary, case-insensitive (\m ... \M).
classificacao as (
    select
        e.texto,
        e.tecnologia_esperada,
        e.deve_cascar,
        e.justificativa,
        e.categoria,
        t.tecnologia as tecnologia_teste,
        case
            when e.texto ~* ('\m' || regexp_replace(t.tecnologia, '([.*+?^${}()|[\]\\])', '\\\1', 'g') || '\M')
            then true
            else false
        end as casou
    from exemplos e
    cross join tecnologias t
),
resultado as (
    select
        texto,
        tecnologia_esperada,
        deve_cascar,
        justificativa,
        categoria,
        tecnologia_teste,
        casou,
        case
            when tecnologia_teste = tecnologia_esperada and deve_cascar = 'sim' and casou then true
            else false
        end as verdadeiro_positivo,
        case
            when tecnologia_teste = tecnologia_esperada and deve_cascar = 'sim' and not casou then true
            else false
        end as falso_negativo,
        case
            when tecnologia_teste = tecnologia_esperada and deve_cascar = 'nao' and casou then true
            else false
        end as falso_positivo,
        case
            when tecnologia_teste = tecnologia_esperada and deve_cascar = 'nao' and not casou then true
            else false
        end as verdadeiro_negativo,
        case
            when tecnologia_teste <> tecnologia_esperada and casou then true
            else false
        end as casou_outra_tecnologia
    from classificacao
),
metricas_por_tecnologia as (
    select
        tecnologia_esperada as tecnologia,
        count(*) filter (where deve_cascar = 'sim') as total_positivos_esperados,
        count(*) filter (where deve_cascar = 'nao') as total_negativos_esperados,
        sum(case when verdadeiro_positivo then 1 else 0 end) as tp,
        sum(case when falso_negativo then 1 else 0 end) as fn,
        sum(case when falso_positivo then 1 else 0 end) as fp,
        sum(case when verdadeiro_negativo then 1 else 0 end) as tn,
        sum(case when casou_outra_tecnologia then 1 else 0 end) as interferencia_outras_techs,
        case
            when (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when falso_positivo then 1 else 0 end)) > 0
            then round(
                sum(case when verdadeiro_positivo then 1 else 0 end)::numeric /
                (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when falso_positivo then 1 else 0 end)),
                4
            )
            else null
        end as precisao,
        case
            when (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when falso_negativo then 1 else 0 end)) > 0
            then round(
                sum(case when verdadeiro_positivo then 1 else 0 end)::numeric /
                (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when falso_negativo then 1 else 0 end)),
                4
            )
            else null
        end as recall,
        case
            when (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when falso_negativo then 1 else 0 end) +
                  sum(case when falso_positivo then 1 else 0 end) + sum(case when verdadeiro_negativo then 1 else 0 end)) > 0
            then round(
                (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when verdadeiro_negativo then 1 else 0 end))::numeric /
                (sum(case when verdadeiro_positivo then 1 else 0 end) + sum(case when falso_negativo then 1 else 0 end) +
                 sum(case when falso_positivo then 1 else 0 end) + sum(case when verdadeiro_negativo then 1 else 0 end)),
                4
            )
            else null
        end as acuracia
    from resultado
    where tecnologia_teste = tecnologia_esperada
    group by tecnologia_esperada
)
select
    tecnologia,
    total_positivos_esperados,
    total_negativos_esperados,
    tp,
    fp,
    fn,
    tn,
    precisao,
    recall,
    acuracia,
    interferencia_outras_techs
from metricas_por_tecnologia
order by tecnologia