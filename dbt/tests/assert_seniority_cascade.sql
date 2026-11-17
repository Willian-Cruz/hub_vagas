-- Teste de dados da macro classify_seniority_cascade (cascata de senioridade).
-- Espelha app/services/seniority_service.py::classificar_senioridade.
-- Usa títulos reais das fixtures (Catho/InfoJobs/Vagas.com, nov/2026) + casos edge
-- conhecidos (PL/SQL, PL-300, rótulo "Liderança", etc.).
-- Precedência: nivel_portal > titulo > descricao_nivel > experiencia_campo > descricao_anos > NULL.
with casos as (
    select * from (values
        -- Títulos reais da Catho/InfoJobs/Vagas.com (fixtures)
        ('Analista de Dados Pleno',           null, null, null, 'Pleno'),
        ('ANALISTA DE SISTEMAS TI PLENO',     null, null, null, 'Pleno'),
        ('Analista de Dados JR',              null, null, null, 'Júnior'),
        ('Anl oper atacado jr análise de dados', null, null, null, 'Júnior'),
        ('Analista de DTI Jr. (Dados e Automação', null, null, null, 'Júnior'),
        ('ANALISTA DE INVENTÁRIO JR',         null, null, null, 'Júnior'),
        ('Analista Tributário Sênior',        null, null, null, 'Sênior'),
        ('ANALISTA DE MARKETING SÊNIOR',      null, null, null, 'Sênior'),
        ('Engenheiro de Dados Sênior',        null, null, null, 'Sênior'),
        ('Analista de Processos Pleno',       null, null, null, 'Pleno'),
        ('Engenheiro Civil Pl - V027803',     null, null, null, 'Pleno'),
        ('Estágio em Engenharia',             null, null, null, 'Estágio/Trainee'),
        ('Especialista em Inteligência Artificial', null, null, null, 'Especialista'),
        ('Coordenador de Engenharia Clínica', null, null, null, 'Coordenador'),
        ('Analista de Dados',                 null, null, null, null),
        -- Casos edge conhecidos (falsos positivos)
        ('Desenvolvedor PL/SQL',              null, null, null, null),
        ('Desenvolvedor PL/SQL Sênior',       null, null, null, 'Sênior'),
        ('Analista Power BI (PL-300)',        null, null, null, null),
        ('Gerente de Dados',                  null, null, null, 'Liderança'),
        ('Diretor de Dados',                  null, null, null, 'Diretoria'),
        -- Nível do portal vence tudo
        ('Analista',                          'Sênior', null, null, 'Sênior'),
        ('Analista Júnior',                   'Pleno', null, null, 'Pleno'),
        -- Campo de experiência (quando não há nível no título)
        ('Analista Financeiro',               null, 'Entre 3 e 5 anos', null, 'Pleno'),
        ('Consultor Comercial',               null, 'Entre 1 e 3 anos', null, 'Júnior'),
        ('Auxiliar Administrativo',           null, 'Só estágios', null, 'Estágio/Trainee'),
        -- Nível explícito na descrição
        ('Analista de Dados',                 null, null, 'Vaga para Analista de Dados Pleno, híbrido.', 'Pleno'),
        ('Analista de Dados',                 null, null, 'Nível: Sênior. Atuação em dados.', 'Sênior'),
        ('Analista',                          null, 'Entre 1 e 3 anos', 'Procuramos Analista Sênior para o time.', 'Sênior'),
        -- Anos de experiência na descrição
        ('Analista de Dados',                 null, null, 'Requisitos: 5+ anos de experiência com SQL', 'Sênior'),
        ('Analista de Dados',                 null, null, 'Experiência de 3 a 5 anos em BI', 'Pleno'),
        -- Sem evidência
        ('Analista de Dados',                 null, null, null, null),
        ('Analista de Dados',                 null, null, 'Pleno domínio de Excel. Empresa com 20 anos de mercado.', null),
    ) as t(titulo, nivel_portal, experiencia, descricao, esperado)
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
