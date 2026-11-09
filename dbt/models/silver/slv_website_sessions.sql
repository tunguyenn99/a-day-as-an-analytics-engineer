select
    (payload ->> 'website_session_id')::bigint as website_session_id,
    (payload ->> 'created_at')::timestamp as created_at,
    (payload ->> 'user_id')::bigint as user_id,
    (payload ->> 'is_repeat_session')::integer as is_repeat_session,
    nullif(trim(payload ->> 'utm_source'), '') as utm_source,
    nullif(trim(payload ->> 'utm_campaign'), '') as utm_campaign,
    nullif(trim(payload ->> 'utm_content'), '') as utm_content,
    nullif(trim(payload ->> 'device_type'), '') as device_type,
    nullif(trim(payload ->> 'http_referer'), '') as http_referer
from {{ ref('brz_website_sessions') }}
