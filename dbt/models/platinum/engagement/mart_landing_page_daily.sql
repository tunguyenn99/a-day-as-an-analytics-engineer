with page_counts as (
    select
        website_session_id,
        count(*) as pageviews
    from {{ ref('fct_pageviews') }}
    group by website_session_id
),

conversions as (
    select distinct website_session_id from {{ ref('fct_orders') }}
),

entry_pages as (
    select
        website_session_id,
        page_key
    from {{ ref('fct_pageviews') }}
    where page_sequence = 1
)

select
    s.session_date,
    e.page_key,
    s.device_key,
    count(*) as sessions,
    count(*) filter (where pc.pageviews = 1) as bounced_sessions,
    count(*) filter (where c.website_session_id is not null) as converted_sessions,
    count(*) filter (where pc.pageviews = 1)::numeric / nullif(count(*), 0) as bounce_rate
from {{ ref('fct_sessions') }} as s
inner join entry_pages as e on s.website_session_id = e.website_session_id
inner join page_counts as pc on s.website_session_id = pc.website_session_id
left join conversions as c on s.website_session_id = c.website_session_id
group by s.session_date, e.page_key, s.device_key
