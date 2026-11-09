select
    (payload ->> 'order_id')::bigint as order_id,
    (payload ->> 'created_at')::timestamp as created_at,
    (payload ->> 'website_session_id')::bigint as website_session_id,
    (payload ->> 'user_id')::bigint as user_id,
    (payload ->> 'primary_product_id')::bigint as primary_product_id,
    (payload ->> 'items_purchased')::integer as items_purchased,
    (payload ->> 'price_usd')::numeric(18, 2) as price_usd,
    (payload ->> 'cogs_usd')::numeric(18, 2) as cogs_usd
from {{ ref('brz_orders') }}
