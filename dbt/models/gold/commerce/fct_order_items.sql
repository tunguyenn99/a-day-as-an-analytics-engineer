select
    order_item_id,
    order_id,
    product_id,
    created_at as sold_at,
    created_at::date as sale_date,
    is_primary_item,
    price_usd as gross_revenue_usd,
    cogs_usd
from {{ ref('slv_order_items') }}
