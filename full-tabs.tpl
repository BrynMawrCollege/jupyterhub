{%- extends 'full.tpl' -%}

{%- block header -%}
{{ super() }}

{%- endblock header -%}

{%- block input_group -%}
    {%- if cell['metadata'].get('format','') == 'tab' -%}
    
    {%- else -%}
        {{ super() }}
    {%- endif -%}
{%- endblock input_group %}
