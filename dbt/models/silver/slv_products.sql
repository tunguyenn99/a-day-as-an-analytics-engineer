select
    (payload ->> 'product_id')::bigint as product_id,
    (payload ->> 'created_at')::timestamp as created_at,
    nullif(trim(payload ->> 'product_name'), '') as product_name
from {{ ref('brz_products') }}
