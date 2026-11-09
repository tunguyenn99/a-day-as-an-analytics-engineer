select * from {{ ref('mart_marketing_daily') }}
where
    session_conversion_rate < 0 or session_conversion_rate > 1
    or converted_sessions > sessions
