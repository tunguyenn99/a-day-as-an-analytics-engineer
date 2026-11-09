select
    (payload ->> 'website_pageview_id')::bigint as website_pageview_id,
    (payload ->> 'created_at')::timestamp as created_at,
    (payload ->> 'website_session_id')::bigint as website_session_id,
    nullif(trim(payload ->> 'pageview_url'), '') as pageview_url
from {{ ref('brz_website_pageviews') }}
