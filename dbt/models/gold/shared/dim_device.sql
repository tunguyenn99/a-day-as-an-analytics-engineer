select distinct
    {{ scd2_key(['device_type']) }} as device_key,
    device_type
from {{ ref('slv_website_sessions') }}
