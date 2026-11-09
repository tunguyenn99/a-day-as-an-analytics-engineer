with sequenced as (
    select
        website_pageview_id,
        website_session_id,
        created_at,
        pageview_url,
        row_number() over (
            partition by website_session_id
            order by created_at, website_pageview_id
        ) as page_sequence,
        lead(created_at) over (
            partition by website_session_id
            order by created_at, website_pageview_id
        ) as next_pageview_at
    from {{ ref('slv_website_pageviews') }}
)

select
    website_pageview_id,
    website_session_id,
    created_at as pageview_at,
    created_at::date as pageview_date,
    {{ scd2_key(['pageview_url']) }} as page_key,
    page_sequence,
    extract(epoch from (next_pageview_at - created_at)) as observed_seconds_to_next_page
from sequenced
