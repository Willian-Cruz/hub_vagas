-- Teste de dados da macro normalize_seniority: espelha as regras do
-- NormalizeService.SENIORIDADE_MAP e do seniority_service._ROTULOS.
-- "PL/SQL", "PL-SQL", "PL SQL" e "PL-300" não são Pleno; o rótulo "Liderança"
-- é aceito como entrada (um nível já classificado assim não vira NULL).
with casos as (
    select * from (values
        ('Pleno',                                       'Pleno'),
        ('Pl',                                          'Pleno'),
        ('Pl/Sr',                                       'Pleno'),
        ('Mid-level',                                   'Pleno'),
        ('Desenvolvedor PL/SQL',                        null),
        ('Desenvolvedor PL-SQL',                        null),
        ('Desenvolvedor PL SQL',                        null),
        ('Analista Power BI (PL-300)',                  null),
        ('Desenvolvedor PL/SQL Sênior',                 'Sênior'),
        ('Engenheiro de Dados Sênior',                  'Sênior'),
        ('Gerência',                                    'Liderança'),
        ('Liderança',                                   'Liderança'),
        ('Lideranca',                                   'Liderança'),
        ('Supervisão/Coordenação',                      'Coordenador'),
        ('Júnior/Trainee',                              'Júnior'),
        ('Técnico',                                     'Técnico'),
        ('Sem experiência',                             null),
        ('Supply Chain',                                null)
    ) as t(texto, esperado)
)
select
    texto,
    esperado,
    {{ normalize_seniority('texto') }} as obtido
from casos
where {{ normalize_seniority('texto') }} is distinct from esperado