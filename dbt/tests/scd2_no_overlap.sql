select a.product_id
from {{ ref('products_history') }} as a
inner join {{ ref('products_history') }} as b
    on a.product_id = b.product_id and a.dbt_scd_id < b.dbt_scd_id
where
    a.dbt_valid_from < coalesce(b.dbt_valid_to, 'infinity'::timestamp)
    and b.dbt_valid_from < coalesce(a.dbt_valid_to, 'infinity'::timestamp)
