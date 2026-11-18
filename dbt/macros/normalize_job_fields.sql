{# Espelha as regras de app/services/normalize_service.py e app/utils/text_utils.py.
   Campo sem informação é NULL, nunca o texto "Não informado". #}

{% macro null_if_placeholder(column_name) %}
case
    when {{ column_name }} is null then null
    when lower(btrim({{ column_name }})) in (
        '', '-', 'n/a',
        'não informado', 'nao informado', 'não informada', 'nao informada',
        'localização não informada', 'localizacao nao informada',
        'confidencial'
    ) then null
    else btrim({{ column_name }})
end
{% endmacro %}

{# include_tecnico = false para inferir pelo título: lá "técnico" costuma ser o
   tipo de trabalho ("Suporte Técnico"), não o nível.
   O PostgreSQL não tem lookahead: "pl" só vira Pleno quando não é PL/SQL nem PL-300. #}
{% macro normalize_seniority(column_name, include_tecnico=true) %}
case
    when {{ column_name }} is null then null
    when {{ column_name }} ~* '\y(jr|j[uú]nior)\y' then 'Júnior'
    when {{ column_name }} ~* '\ypleno\y' then 'Pleno'
    when {{ column_name }} ~* '\ymid[- ]?level\y' then 'Pleno'
    when {{ column_name }} ~* '\ypl\y'
         and {{ column_name }} !~* '\ypl\s*[/-]?\s*sql\y'
         and {{ column_name }} !~* '\ypl[/-]\s*[0-9]'
         then 'Pleno'
    when {{ column_name }} ~* '\y(sr|s[eê]nior)\y' then 'Sênior'
    when {{ column_name }} ~* '\y(especialista|specialist)\y' then 'Especialista'
    when {{ column_name }} ~* '\y(coordena[cç][aã]o|coordenadora?|coordinator|supervis[aã]o|supervisora?)\y' then 'Coordenador'
    when {{ column_name }} ~* '\y(gerente|ger[eê]ncia|manager|l[ií]deran[cç]a|l[ií]der|leader|lead)\y' then 'Liderança'
    when {{ column_name }} ~* '\y(diretora?|diretoria|director|head|vp)\y' then 'Diretoria'
    when {{ column_name }} ~* '\y(trainee|est[aá]gi[oó]s?|estagi[aá]ri[oa]s?)\y' then 'Estágio/Trainee'
    -- Os próprios rótulos são aceitos como entrada: "Liderança" não casa com nenhuma
    -- palavra da regra acima, então um nível já classificado assim virava NULL.
    -- O `fold_text` tira acentos e minúscula, espelhando o sem_acentos().casefold()
    -- do Python: "Liderança" e "Lideranca" batem no mesmo valor.
    when {{ fold_text(column_name) }} = 'estagio/trainee' then 'Estágio/Trainee'
    when {{ fold_text(column_name) }} = 'junior' then 'Júnior'
    when {{ fold_text(column_name) }} = 'pleno' then 'Pleno'
    when {{ fold_text(column_name) }} = 'senior' then 'Sênior'
    when {{ fold_text(column_name) }} = 'especialista' then 'Especialista'
    when {{ fold_text(column_name) }} = 'coordenador' then 'Coordenador'
    when {{ fold_text(column_name) }} = 'lideranca' then 'Liderança'
    when {{ fold_text(column_name) }} = 'diretoria' then 'Diretoria'
    {% if include_tecnico %}
    when {{ column_name }} ~* '\yt[eé]cnic[oa]\y' then 'Técnico'
    {% endif %}
    else null
end
{% endmacro %}

{% macro _normalize_location_text(column_name) %}
regexp_replace(
    regexp_replace(
        replace(replace(btrim({{ column_name }}), '/', ' - '), ',', ' - '),
        '\s+', ' ', 'g'
    ),
    '\s*-\s*(?=[[:alpha:]]{2}$)', ' - '
)
{% endmacro %}

{# Cidade em minúsculas nas preposições ("Rio de Janeiro"), como no Python. #}
{% macro _capitalize_city(expr) %}
replace(replace(replace(replace(replace(replace(
    initcap(lower({{ expr }})),
    ' De ', ' de '), ' Da ', ' da '), ' Do ', ' do '),
    ' Das ', ' das '), ' Dos ', ' dos '), ' D''', ' d''')
{% endmacro %}

{% macro normalize_location(column_name) %}
case
    when {{ column_name }} is null then null
    when {{ column_name }} ~* '(remoto|remote|home.?office|trabalho remoto)' then 'Remoto'
    when {{ column_name }} ~* '(h[ií]brido|hybrid)' then 'Híbrido'
    when {{ _normalize_location_text(column_name) }} ~ ' - [[:alpha:]]{2}$'
        then {{ _capitalize_city("left(" ~ _normalize_location_text(column_name) ~ ", length(" ~ _normalize_location_text(column_name) ~ ") - 5)") }}
             || ' - ' || upper(right({{ _normalize_location_text(column_name) }}, 2))
    else {{ _capitalize_city(_normalize_location_text(column_name)) }}
end
{% endmacro %}

{# Presencial / Híbrido / Remoto, ou NULL se o texto não for reconhecido. #}
{% macro normalize_modality(column_name) %}
case
    when {{ column_name }} is null then null
    when {{ column_name }} ~* '(home.?office|remoto|remote)' then 'Remoto'
    when {{ column_name }} ~* '(h[ií]brido|hybrid)' then 'Híbrido'
    when {{ column_name }} ~* 'presencial' then 'Presencial'
    else null
end
{% endmacro %}

{# Salário informado pelo portal; senão, valor "R$ ..." achado na descrição.
   Retorna NULL quando não há nenhum dos dois. "A combinar" só vem do portal,
   nunca é infirido da descrição. #}
{% macro extract_salary(salary_column, description_column) %}
case
    when {{ salary_column }} is not null then {{ salary_column }}
    when coalesce({{ description_column }}, '') ~* 'r\$\s*[0-9]'
        then regexp_replace(
            substring({{ description_column }} from '(?i)r\$\s*[0-9.,]+'),
            'r\$', 'R$', 'i'
        )
    else null
end
{% endmacro %}

{# Parse de salário em texto para valor numérico mínimo.
   Remove "R$", pontos de milhares e vírgula decimal. #}
{% macro salario_min(salario_texto_column) %}
case
    when {{ salario_texto_column }} is null then null
    when lower({{ salario_texto_column }}) ~ 'a combinar' then null
    when {{ salario_texto_column }} ~* 'r\$\s*([0-9.,]+)\s*(?:a|à|-)\s*r\$\s*([0-9.,]+)' then
        replace(
            regexp_replace(
                substring({{ salario_texto_column }} from '(?i)r\$\s*([0-9.,]+)\s*(?:a|à|-)'),
                '[^0-9,]', '', 'g'
            ),
            ',', '.'
        )::numeric
    when {{ salario_texto_column }} ~* 'r\$\s*([0-9.,]+)' then
        replace(
            regexp_replace(
                substring({{ salario_texto_column }} from '(?i)r\$\s*([0-9.,]+)'),
                '[^0-9,]', '', 'g'
            ),
            ',', '.'
        )::numeric
    else null
end
{% endmacro %}

{# Parse de salário em texto para valor numérico máximo. #}
{% macro salario_max(salario_texto_column) %}
case
    when {{ salario_texto_column }} is null then null
    when lower({{ salario_texto_column }}) ~ 'a combinar' then null
    when {{ salario_texto_column }} ~* 'r\$\s*([0-9.,]+)\s*(?:a|à|-)\s*r\$\s*([0-9.,]+)' then
        replace(
            regexp_replace(
                substring({{ salario_texto_column }} from '(?i)(?:a|à|-)\s*r\$\s*([0-9.,]+)'),
                '[^0-9,]', '', 'g'
            ),
            ',', '.'
        )::numeric
    when {{ salario_texto_column }} ~* 'r\$\s*([0-9.,]+)' then
        replace(
            regexp_replace(
                substring({{ salario_texto_column }} from '(?i)r\$\s*([0-9.,]+)'),
                '[^0-9,]', '', 'g'
            ),
            ',', '.'
        )::numeric
    else null
end
{% endmacro %}

{# Classifica o tipo de salário com base no texto publicado. #}
{% macro salario_tipo(salario_texto_column) %}
case
    when {{ salario_texto_column }} is null then 'nao_informado'
    when lower({{ salario_texto_column }}) ~ 'a combinar' then 'a_combinar'
    when {{ salario_texto_column }} ~* 'r\$\s*([0-9.,]+)\s*(?:a|à|-)\s*r\$\s*([0-9.,]+)' then 'faixa'
    when {{ salario_texto_column }} ~* 'r\$\s*([0-9.,]+)' then 'exato'
    else 'nao_informado'
end
{% endmacro %}

{# Texto sem acento, minúsculo e com espaços colapsados, para chaves de comparação. #}
{% macro fold_text(column_name) %}
regexp_replace(
    translate(lower(btrim({{ column_name }})),
              'áàâãäéèêëíìîïóòôõöúùûüçñÇ',
              'aaaaaeeeeiiiiooooouuuucnn'),
    '\s+', ' ', 'g'
)
{% endmacro %}
