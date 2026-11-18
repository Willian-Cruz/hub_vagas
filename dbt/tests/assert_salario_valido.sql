{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Regra de negócio de salário: salario_min não pode ser maior '
                      'que salario_max; valores negativos são inválidos; quando '
                      'salario_tipo = a_combinar, ambos devem ser NULL; quando '
                      'salario_tipo = faixa, ambos devem estar preenchidos.'
    }
  )
}}

-- Validações de integridade de salário na Silver.
-- Retorna linhas que violam as regras de negócio (falha se houver resultado).
with invalidos as (
    select
        raw_job_id,
        origem,
        titulo,
        salario_texto,
        salario_min,
        salario_max,
        salario_tipo,
        'salario_min_maior_que_max' as motivo
    from {{ ref('jobs') }}
    where salario_min is not null
      and salario_max is not null
      and salario_min > salario_max

    union all

    select
        raw_job_id,
        origem,
        titulo,
        salario_texto,
        salario_min,
        salario_max,
        salario_tipo,
        'valor_negativo' as motivo
    from {{ ref('jobs') }}
    where (salario_min is not null and salario_min < 0)
       or (salario_max is not null and salario_max < 0)

    union all

    select
        raw_job_id,
        origem,
        titulo,
        salario_texto,
        salario_min,
        salario_max,
        salario_tipo,
        'a_combinar_com_valor' as motivo
    from {{ ref('jobs') }}
    where lower(coalesce(salario_tipo, '')) = 'a_combinar'
      and (salario_min is not null or salario_max is not null)

    union all

    select
        raw_job_id,
        origem,
        titulo,
        salario_texto,
        salario_min,
        salario_max,
        salario_tipo,
        'faixa_sem_valores' as motivo
    from {{ ref('jobs') }}
    where lower(coalesce(salario_tipo, '')) = 'faixa'
      and (salario_min is null or salario_max is null)
)
select * from invalidos
