with sales as (
    select
        order_date,
        count(*) as orders,
        sum(gross_revenue_usd) as gross_revenue_usd,
        sum(cogs_usd) as cogs_usd
    from {{ ref('fct_orders') }}
    group by order_date
),

refunds as (
    select
        refund_date,
        count(*) as refund_events,
        sum(refund_amount_usd) as refund_amount_usd
    from {{ ref('fct_refunds') }}
    group by refund_date
)

select
    d.date_day,
    coalesce(s.orders, 0) as orders,
    coalesce(r.refund_events, 0) as refund_events,
    coalesce(s.gross_revenue_usd, 0) as gross_revenue_usd,
    coalesce(s.cogs_usd, 0) as cogs_usd,
    coalesce(r.refund_amount_usd, 0) as refund_amount_usd,
    coalesce(s.gross_revenue_usd, 0) - coalesce(r.refund_amount_usd, 0) as net_revenue_usd,
    coalesce(s.gross_revenue_usd, 0) - coalesce(r.refund_amount_usd, 0)
    - coalesce(s.cogs_usd, 0) as gross_profit_after_refunds_usd
from {{ ref('dim_date') }} as d
left join sales as s on d.date_day = s.order_date
left join refunds as r on d.date_day = r.refund_date
