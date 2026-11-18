{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Avalia precisão e recall da classificação de tecnologias '
                      'usando um conjunto rotulado manualmente. Retorna apenas '
                      'violações reais (falsos positivos e falsos negativos). '
                      'Se não houver violações, o teste passa sem retornar linhas.'
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
-- Aplica o mesmo regex usado nos marts: word boundary, case-insensitive (\m ... \M).
classificacao as (
    select
        e.texto,
        e.tecnologia_esperada,
        e.deve_cascar,
        t.tecnologia as tecnologia_teste,
        case
            when e.texto ~* ('\m' || regexp_replace(t.tecnologia, '([.*+?^${}()|[\]\\])', '\\\1', 'g') || '\M')
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
-- Violações reais: falsos negativos (deve cascar mas não casou)
-- e falsos positivos (não deve cascar mas casou).
violacoes as (
    select
        texto,
        tecnologia_esperada,
        deve_cascar,
        caso
    from (
        select
            texto,
            tecnologia_esperada,
            deve_cascar,
            'falso_negativo' as caso
        from resultado
        where deve_cascar = 'sim'
          and not esperado_casou
        union all
        select
            texto,
            tecnologia_esperada,
            deve_cascar,
            'falso_positivo' as caso
        from resultado
        where deve_cascar = 'não'
          and falso_positivo_qualquer
    ) v
)
select
    texto,
    tecnologia_esperada,
    deve_cascar,
    tipo_violacao
from (
    select
        texto,
        tecnologia_esperada,
        deve_cascar,
        caso as tipo_violacao
    from violacoes
) v
