{% snapshot products_history %}
{{ config(
    target_schema=target.schema ~ '_history',
    unique_key='product_id', strategy='check', check_cols=['product_name'],
    invalidate_hard_deletes=True
) }}
select product_id, product_name from {{ ref('slv_products') }}
{% endsnapshot %}
