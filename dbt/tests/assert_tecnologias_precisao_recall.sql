{{
  config(
    severity = 'warn',
    meta = {
      'documentacao': 'Avalia precisão e recall da classificação de tecnologias '
                      'usando um conjunto rotulado manualmente. Não define meta '
                      'de precisão (baseline deve ser estabelecida primeiro); '
                      'apenas mede e reporta falsos positivos e falsos negativos.'
    }
  )
}}

-- Conjunto de validação rotulado para classificação de tecnologias.
-- Para cada exemplo, verifica se o regex do dbt (word boundary, case-insensitive)
-- casa corretamente com a tecnologia esperada.
with exemplos as (
    select * from {{ ref('classificacao_tecnologias_validacao') }}
),
tecnologias as (
    select tecnologia from {{ ref('tecnologias_monitoradas') }}
),
-- Aplica o mesmo regex usado nos marts: word boundary, case-insensitive.
classificacao as (
    select
        e.texto,
        e.tecnologia_esperada,
        e.deve_cascar,
        t.tecnologia as tecnologia_teste,
        case
            when e.texto ~* ('\m' || t.tecnologia || '\M')
            then true
            else false
        end as casou
    from exemplos e
    cross join tecnologias t
),
-- Para cada exemplo, verifica se a tecnologia esperada casou (quando deve) ou não casou (quando não deve).
resultado as (
    select
        texto,
        tecnologia_esperada,
        deve_cascar,
        bool_or(case when tecnologia_teste = tecnologia_esperada then casou else false end) as esperado_casou,
        bool_or(case when tecnologia_teste <> tecnologia_esperada then casou else false end) as falso_positivo_qualquer
    from classificacao
    group by texto, tecnologia_esperada, deve_cascar
),
metricas as (
    select
        count(*) filter (where deve_cascar = 'sim' and esperado_casou) as verdadeiros_positivos,
        count(*) filter (where deve_cascar = 'sim' and not esperado_casou) as falsos_negativos,
        count(*) filter (where deve_cascar = 'não' and falso_positivo_qualquer) as falsos_positivos,
        count(*) filter (where deve_cascar = 'não' and not falso_positivo_qualquer) as verdadeiros_negativos
    from resultado
)
select
    verdadeiros_positivos,
    falsos_negativos,
    falsos_positivos,
    verdadeiros_negativos,
    round(
        100.0 * verdadeiros_positivos::numeric / nullif(verdadeiros_positivos + falsos_negativos, 0),
        1
    ) as recall_percent,
    round(
        100.0 * verdadeiros_positivos::numeric / nullif(verdadeiros_positivos + falsos_positivos, 0),
        1
    ) as precisao_percent
from metricas
