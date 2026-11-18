{{
  config(
    materialized = 'view',
    meta = {
      'documentacao': 'Model de teste da macro normalize_seniority. '
                      'Cada linha é um caso: título de entrada e senioridade esperada.'
    }
  )
}}

with casos as (
    select *
    from (values
        ('Desenvolvedor PL/SQL', null),
        ('Desenvolvedor PL-SQL', null),
        ('Desenvolvedor PL SQL', null),
        ('Analista Power BI (PL-300)', null),
        ('Desenvolvedor Pl', 'Pleno'),
        ('Pl/Sr', 'Pleno'),
        ('Analista Mid-level', 'Pleno'),
        ('Engenheiro de Dados Sênior', 'Sênior'),
        ('Engenheiro Civil Pl - V027803', 'Pleno'),
        ('Estágio Em Análise De Dados', 'Estágio/Trainee'),
        ('Liderança', 'Liderança'),
        ('Lideranca', 'Liderança'),
        ('Gerente de Projetos', 'Liderança'),
        ('Tech Lead', 'Liderança'),
        ('Supply Chain Analyst', null),
        ('Employee Relations', null),
        ('Sem experiência', null),
        (null, null)
    ) as t(titulo, esperado)
)
select
    {{ normalize_seniority('titulo', include_tecnico=false) }} as senioridade_normalizada,
    esperado,
    titulo
from casos
