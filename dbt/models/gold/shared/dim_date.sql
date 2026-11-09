with event_dates as (
    select created_at::date as event_date from {{ ref('slv_website_sessions') }}
    union all
    select created_at::date from {{ ref('slv_orders') }}
    union all
    select created_at::date from {{ ref('slv_order_item_refunds') }}
),

bounds as (
    select
        min(event_date) as first_date,
        max(event_date) as last_date
    from event_dates
)

select
    d::date as date_day,
    extract(year from d)::integer as year_number,
    extract(month from d)::integer as month_number,
    date_trunc('month', d)::date as month_start,
    extract(isodow from d)::integer as iso_day_of_week
from bounds
cross join lateral generate_series(first_date::timestamp, last_date::timestamp, interval '1 day') as d
