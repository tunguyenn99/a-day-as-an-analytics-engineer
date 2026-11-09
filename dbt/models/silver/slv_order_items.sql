select
    (payload ->> 'order_item_id')::bigint as order_item_id,
    (payload ->> 'created_at')::timestamp as created_at,
    (payload ->> 'order_id')::bigint as order_id,
    (payload ->> 'product_id')::bigint as product_id,
    (payload ->> 'is_primary_item')::integer as is_primary_item,
    (payload ->> 'price_usd')::numeric(18, 2) as price_usd,
    (payload ->> 'cogs_usd')::numeric(18, 2) as cogs_usd
from {{ ref('brz_order_items') }}
