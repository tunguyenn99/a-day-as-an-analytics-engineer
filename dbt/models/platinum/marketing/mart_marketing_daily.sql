with orders_by_session as (
    select
        website_session_id,
        count(*) as orders,
        sum(gross_revenue_usd) as gross_revenue_usd
    from {{ ref('fct_orders') }}
    group by website_session_id
)

-- ST06 misreads the ::bigint cast (kept for the contract) as a simple target.
select  -- noqa: ST06
    s.session_date,
    s.channel_key,
    s.device_key,
    count(*) as sessions,
    count(*) filter (where o.orders > 0) as converted_sessions,
    sum(coalesce(o.orders, 0))::bigint as orders,
    sum(coalesce(o.gross_revenue_usd, 0)) as gross_revenue_usd,
    count(*) filter (where o.orders > 0)::numeric / nullif(count(*), 0) as session_conversion_rate,
    sum(coalesce(o.gross_revenue_usd, 0)) / nullif(count(*), 0) as revenue_per_session_usd
from {{ ref('fct_sessions') }} as s
left join orders_by_session as o on s.website_session_id = o.website_session_id
group by s.session_date, s.channel_key, s.device_key
