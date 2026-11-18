{{
  config(
    severity = 'error',
    meta = {
      'documentacao': 'Teste de borda da normalização de senioridade (dbt macro). '
                      'Falha se PL/SQL, PL-SQL, PL SQL ou PL-300 forem mapeados como Pleno, '
                      'ou se "Liderança" não for reconhecida.'
    }
  )
}}

-- Verifica que cada caso de teste produz a senioridade esperada.
-- PL/SQL, PL-SQL, PL SQL, PL-300 → NULL (não são Pleno)
-- Liderança / Lideranca → Liderança
-- Outros casos mapeados conforme o esperado
select *
from {{ ref('__test_seniority_normalization') }}
where senioridade_normalizada is distinct from esperado
