select distinct
    {{ scd2_key(['utm_source', 'utm_campaign', 'utm_content', 'http_referer']) }} as channel_key,
    utm_source, utm_campaign, utm_content, http_referer,
    case
        when utm_source is not null then 'tagged_campaign'
        when http_referer is not null then 'untagged_referral'
        else 'direct_or_unknown'
    end as channel_group
from {{ ref('slv_website_sessions') }}
