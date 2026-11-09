select
    (payload ->> 'order_item_refund_id')::bigint as order_item_refund_id,
    (payload ->> 'created_at')::timestamp as created_at,
    (payload ->> 'order_item_id')::bigint as order_item_id,
    (payload ->> 'order_id')::bigint as order_id,
    (payload ->> 'refund_amount_usd')::numeric(18, 2) as refund_amount_usd
from {{ ref('brz_order_item_refunds') }}
