select distinct
    {{ scd2_key(['pageview_url']) }} as page_key,
    pageview_url,
    case
        when pageview_url = '/products' then 'products'
        when pageview_url in (
            '/the-original-mr-fuzzy', '/the-forever-love-bear',
            '/the-birthday-sugar-panda', '/the-hudson-river-mini-bear'
        ) then 'product_detail'
        when pageview_url = '/cart' then 'cart'
        when pageview_url = '/shipping' then 'shipping'
        when pageview_url in ('/billing', '/billing-2') then 'billing'
        when pageview_url = '/thank-you-for-your-order' then 'thank_you'
        when pageview_url = '/home' or pageview_url like '/lander-%' then 'landing'
        else 'other'
    end as page_category
from {{ ref('slv_website_pageviews') }}
