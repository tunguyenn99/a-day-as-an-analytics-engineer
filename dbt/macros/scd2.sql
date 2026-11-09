{% macro scd2_key(columns) -%}
md5(jsonb_build_array({{ columns | join(', ') }})::text)
{%- endmacro %}

{% macro scd2_current(relation) -%}
select * from {{ relation }} where dbt_valid_to is null
{%- endmacro %}
