select
    dbt_scd_id as product_version_key,
    product_id,
    product_name,
    dbt_valid_from as observed_valid_from,
    dbt_valid_to as observed_valid_to,
    dbt_valid_to is null as is_current
from {{ ref('products_history') }}
