with sessions as (
    select
        user_id,
        min(created_at) as first_session_at,
        count(*) as lifetime_sessions
    from {{ ref('slv_website_sessions') }}
    where user_id is not null
    group by user_id
),

orders as (
    select
        user_id,
        min(created_at) as first_order_at,
        count(*) as lifetime_orders
    from {{ ref('slv_orders') }}
    where user_id is not null
    group by user_id
)

select
    s.first_session_at,
    o.first_order_at,
    coalesce(s.user_id, o.user_id) as user_id,
    coalesce(s.lifetime_sessions, 0) as lifetime_sessions,
    coalesce(o.lifetime_orders, 0) as lifetime_orders
from sessions as s
full outer join orders as o on s.user_id = o.user_id
