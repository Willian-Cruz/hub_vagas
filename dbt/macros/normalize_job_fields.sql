{% macro normalize_seniority(column_name) %}
case
    when {{ column_name }} is null then 'Não informado'
    when {{ column_name }} ~* '(jr\.?|j[uú]nior|junior)' then 'Júnior'
    when {{ column_name }} ~* '(pl\.?|pleno)' then 'Pleno'
    when {{ column_name }} ~* '(sr\.?|s[eê]nior|senior)' then 'Sênior'
    when {{ column_name }} ~* '(especialista|specialist)' then 'Especialista'
    when {{ column_name }} ~* '(coordenador|coordinator)' then 'Coordenador'
    when {{ column_name }} ~* '(gerente|manager|líder|lider|lead)' then 'Liderança'
    when {{ column_name }} ~* '(diretor|director|head|vp\b)' then 'Diretoria'
    when {{ column_name }} ~* '(trainee|est[aá]gi[oó]|estagi[aá]rio)' then 'Estágio/Trainee'
    else 'Não informado'
end
{% endmacro %}

{% macro _normalize_location_text(column_name) %}
regexp_replace(
    regexp_replace(
        replace(replace(trim({{ column_name }}), '/', ' - '), ',', ' - '),
        '\s+', ' ', 'g'
    ),
    '\s*-\s*', ' - ', 'g'
)
{% endmacro %}

{% macro normalize_location(column_name) %}
case
    when {{ column_name }} is null
      or lower(trim({{ column_name }})) in ('', 'não informado', 'nao informado')
        then 'Não informado'
    when {{ column_name }} ~* '(remoto|remote|home[ -]?office|trabalho remoto)'
        then 'Remoto'
    when {{ column_name }} ~* '(híbrido|hibrido|hybrid)'
        then 'Híbrido'
    else
        case
            when {{ _normalize_location_text(column_name) }} ~ ' - [[:alpha:]]{2}$'
            then initcap(left(
                {{ _normalize_location_text(column_name) }},
                length({{ _normalize_location_text(column_name) }}) - 2
            )) || upper(right({{ _normalize_location_text(column_name) }}, 2))
            else initcap({{ _normalize_location_text(column_name) }})
        end
end
{% endmacro %}

{% macro extract_salary(salary_column, description_column) %}
case
    when {{ salary_column }} is not null
      and lower(trim({{ salary_column }})) not in ('', 'não informado', 'nao informado')
        then trim({{ salary_column }})
    when coalesce({{ description_column }}, '') ~* '(a\s+combinar|confidencial|não\s+divulgado|sigiloso)'
        then 'A combinar'
    when coalesce({{ description_column }}, '') ~* 'r\$\s*[0-9]'
        then regexp_replace(
            substring({{ description_column }} from 'r\$\s*[0-9.,]+'),
            'r\$', 'R$', 'i'
        )
    else 'Não informado'
end
{% endmacro %}
