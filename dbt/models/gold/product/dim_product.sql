select
    product_id,
    created_at as launched_at,
    product_name
from {{ ref('slv_products') }}
