select * from {{ ref('mart_funnel_daily') }}
where
    sessions < reached_products or reached_products < reached_cart
    or reached_cart < reached_shipping or reached_shipping < reached_billing
    or reached_billing < reached_thank_you
