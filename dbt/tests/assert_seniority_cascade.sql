-- Teste de dados da macro classify_seniority_cascade (cascata de senioridade).
-- Verifica casos onde a classificação é direta e óbvia.
with casos as (
    select cast('Analista de Dados Pleno' as text) as titulo, cast(null as text) as nivel_portal, cast(null as text) as experiencia, cast(null as text) as descricao, cast('Pleno' as text) as esperado
    union all select cast('ANALISTA DE SISTEMAS TI PLENO' as text), null, null, null, cast('Pleno' as text)
    union all select cast('Analista de Dados JR' as text), null, null, null, cast('Júnior' as text)
    union all select cast('Analista Tributário Sênior' as text), null, null, null, cast('Sênior' as text)
    union all select cast('Engenheiro de Dados Sênior' as text), null, null, null, cast('Sênior' as text)
    union all select cast('Estágio em Engenharia' as text), null, null, null, cast('Estágio/Trainee' as text)
    union all select cast('Especialista em Inteligência Artificial' as text), null, null, null, cast('Especialista' as text)
    union all select cast('Coordenador de Engenharia Clínica' as text), null, null, null, cast('Coordenador' as text)
    union all select cast('Diretor de Dados' as text), null, null, null, cast('Diretoria' as text)
    -- Nível do portal vence tudo
    union all select cast('Analista' as text), cast('Sênior' as text), null, null, cast('Sênior' as text)
    -- Sem evidência → NULL
    union all select cast('Analista de Dados' as text), null, null, null, null
)
select
    titulo,
    nivel_portal,
    experiencia,
    descricao,
    esperado,
    {{ classify_seniority_cascade('nivel_portal', 'titulo', 'experiencia', 'descricao') }} as obtido
from casos
where {{ classify_seniority_cascade('nivel_portal', 'titulo', 'experiencia', 'descricao') }} is distinct from esperado
