with source_totals as (
    select sum(price_usd) as revenue from {{ ref('slv_orders') }}
),

refund_totals as (
    select sum(refund_amount_usd) as refunds from {{ ref('slv_order_item_refunds') }}
),

mart_totals as (
    select
        sum(gross_revenue_usd) as revenue,
        sum(refund_amount_usd) as refunds,
        sum(net_revenue_usd) as net_revenue
    from {{ ref('mart_finance_daily') }}
)

select m.* from mart_totals as m cross join source_totals as s cross join refund_totals as r
where
    abs(coalesce(m.revenue, 0) - coalesce(s.revenue, 0)) > 0.01
    or abs(coalesce(m.refunds, 0) - coalesce(r.refunds, 0)) > 0.01
    or abs(coalesce(m.net_revenue, 0) - (coalesce(s.revenue, 0) - coalesce(r.refunds, 0))) > 0.01
