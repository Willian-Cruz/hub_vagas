{#
  Macro dbt que espelha app/services/seniority_service.py::classificar_senioridade.
  Recebe 4 colunas (todas opcionais via CASE WHEN null then null):
    - nivel_portal: nível informado diretamente pelo portal (ex: ícone "seniority" do InfoJobs)
    - titulo: título da vaga
    - experiencia: campo de experiência do portal (ex: "Entre 3 e 5 anos", "Sem experiência")
    - descricao: texto da descrição da vaga
  
  Ordem de precedência (igual ao Python):
    1. nivel_portal (se vier preenchido, usa normalize_seniority direto)
    2. titulo (se vier preenchido, usa normalize_seniority com include_tecnico=false)
    3. nível explícito na descrição (padrão "Nível: Pleno" ou "Analista Sênior")
    4. nível pelo campo de experiência (faixas: <3=Júnior, 3-5=Pleno, >=5=Sênior)
    5. "N anos de experiência" na descrição (padrão forte)
    6. NULL se nada casar
#}

{% macro classify_seniority_cascade(nivel_portal, titulo, experiencia, descricao) %}
{% set np = normalize_seniority(nivel_portal) %}
{% set tt = normalize_seniority(titulo, include_tecnico=false) %}

case
    when {{ np }} is not null then {{ np }}
    when {{ tt }} is not null then {{ tt }}
    
    {# 3. nível explícito na descrição: "Nível: Pleno", "Analista de Dados Sênior" #}
    when descricao ~* '\b(?:nivel|senioridade|categoria)\s*[:\-]?\s*(junior|pleno|senior|especialista)\b' then
        case
            when descricao ~* '\bjunior\b' then 'Júnior'
            when descricao ~* '\bpleno\b' then 'Pleno'
            when descricao ~* '\bsenior\b' then 'Sênior'
            when descricao ~* '\bespecialista\b' then 'Especialista'
            else null
        end
    
    {# 4. nível pelo campo de experiência do portal #}
    when experiencia is not null then
        case
            {% set faixas = [(0, 3, 'Júnior'), (3, 5, 'Pleno'), (5, None, 'Sênior')] %}
            {% for min_anos, max_anos, nivel in faixas %}
                {% if max_anos is none %}
                    when cast(regexp_replace(experiencia, '[^0-9]', '') as integer) >= {{ min_anos }} then '{{ nivel }}'
                {% else %}
                    when cast(regexp_replace(experiencia, '[^0-9]', '') as integer) >= {{ min_anos }}
                         and cast(regexp_replace(experiencia, '[^0-9]', '') as integer) < {{ max_anos }} then '{{ nivel }}'
                {% endif %}
            {% endfor %}
        end
    
    {# 5. "N anos de experiência" na descrição #}
    when descricao ~* '(\d+)\s*anos?\s*de\s*experiencia' then
        case
            when cast(regexp_replace(regexp_replace(descricao, '[^0-9]', ''), '^0*', '') as integer) < 3 then 'Júnior'
            when cast(regexp_replace(regexp_replace(descricao, '[^0-9]', ''), '^0*', '') as integer) < 5 then 'Pleno'
            else 'Sênior'
        end
    
    else null
end
{% endmacro %}