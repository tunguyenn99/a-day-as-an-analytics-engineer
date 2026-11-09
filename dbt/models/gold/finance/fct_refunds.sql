select
    order_item_refund_id,
    order_item_id,
    order_id,
    created_at as refunded_at,
    created_at::date as refund_date,
    refund_amount_usd
from {{ ref('slv_order_item_refunds') }}
