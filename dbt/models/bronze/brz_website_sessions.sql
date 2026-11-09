select
    source_record_id,
    record_hash,
    payload,
    ingested_at,
    extraction_id
from {{ source('landing', 'website_sessions') }}
