select
    order_id,
    created_at as ordered_at,
    created_at::date as order_date,
    website_session_id,
    user_id,
    primary_product_id,
    items_purchased,
    price_usd as gross_revenue_usd,
    cogs_usd
from {{ ref('slv_orders') }}
