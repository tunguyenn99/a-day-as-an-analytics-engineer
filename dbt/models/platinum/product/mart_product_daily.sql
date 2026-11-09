with refunds_by_item as (
    select
        order_item_id,
        sum(refund_amount_usd) as refund_amount_usd,
        count(*) as refund_events
    from {{ ref('fct_refunds') }}
    group by order_item_id
)

select
    i.sale_date,
    i.product_id,
    count(*) as units_sold,
    count(distinct i.order_id) as orders,
    count(*) filter (where r.refund_events > 0) as refunded_units,
    sum(i.gross_revenue_usd) as gross_revenue_usd,
    sum(i.cogs_usd) as cogs_usd,
    sum(coalesce(r.refund_amount_usd, 0)) as refund_amount_usd,
    sum(i.gross_revenue_usd - coalesce(r.refund_amount_usd, 0)) as net_revenue_usd,
    count(*) filter (where r.refund_events > 0)::numeric / nullif(count(*), 0) as unit_refund_rate
from {{ ref('fct_order_items') }} as i
left join refunds_by_item as r on i.order_item_id = r.order_item_id
group by i.sale_date, i.product_id
