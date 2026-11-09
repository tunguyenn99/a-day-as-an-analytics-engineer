select
    website_session_id, created_at as session_started_at,
    created_at::date as session_date, user_id, is_repeat_session,
    {{ scd2_key(['utm_source', 'utm_campaign', 'utm_content', 'http_referer']) }} as channel_key,
    {{ scd2_key(['device_type']) }} as device_key
from {{ ref('slv_website_sessions') }}
