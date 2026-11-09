with items as (
    select
        order_id,
        count(*) as units,
        sum(gross_revenue_usd) as revenue,
        sum(cogs_usd) as cogs
    from {{ ref('fct_order_items') }}
    group by order_id
)

select o.order_id from {{ ref('fct_orders') }} as o
left join items as i on o.order_id = i.order_id
where
    i.order_id is null or i.units <> o.items_purchased
    or abs(i.revenue - o.gross_revenue_usd) > 0.01 or abs(i.cogs - o.cogs_usd) > 0.01
