{% macro generate_schema_name(custom_schema_name, node) -%}
    {#
        Override default dbt behavior which concatenates the profile schema
        with the custom schema (e.g., RAW_STAGING). Instead, use the custom
        schema name directly when one is specified, or fall back to the
        profile's default schema.
    #}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
