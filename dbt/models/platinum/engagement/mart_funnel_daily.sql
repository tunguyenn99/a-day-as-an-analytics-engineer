with page_steps as (
    select
        v.website_session_id,
        v.page_sequence,
        p.page_category
    from {{ ref('fct_pageviews') }} as v
    inner join {{ ref('dim_page') }} as p on v.page_key = p.page_key
),

products as (
    select
        website_session_id,
        min(page_sequence) as step
    from page_steps
    where page_category = 'products'
    group by website_session_id
),

cart as (
    select
        p.website_session_id,
        min(v.page_sequence) as step
    from products as p inner join page_steps as v
        on p.website_session_id = v.website_session_id and p.step < v.page_sequence
    where v.page_category = 'cart'
    group by p.website_session_id
),

shipping as (
    select
        c.website_session_id,
        min(v.page_sequence) as step
    from cart as c inner join page_steps as v
        on c.website_session_id = v.website_session_id and c.step < v.page_sequence
    where v.page_category = 'shipping'
    group by c.website_session_id
),

billing as (
    select
        s.website_session_id,
        min(v.page_sequence) as step
    from shipping as s inner join page_steps as v
        on s.website_session_id = v.website_session_id and s.step < v.page_sequence
    where v.page_category = 'billing'
    group by s.website_session_id
),

completed as (
    select
        b.website_session_id,
        min(v.page_sequence) as step
    from billing as b inner join page_steps as v
        on b.website_session_id = v.website_session_id and b.step < v.page_sequence
    where v.page_category = 'thank_you'
    group by b.website_session_id
)

select
    s.session_date,
    s.device_key,
    count(*) as sessions,
    count(p.step) as reached_products,
    count(c.step) as reached_cart,
    count(sh.step) as reached_shipping,
    count(b.step) as reached_billing,
    count(co.step) as reached_thank_you
from {{ ref('fct_sessions') }} as s
left join products as p on s.website_session_id = p.website_session_id
left join cart as c on s.website_session_id = c.website_session_id
left join shipping as sh on s.website_session_id = sh.website_session_id
left join billing as b on s.website_session_id = b.website_session_id
left join completed as co on s.website_session_id = co.website_session_id
group by s.session_date, s.device_key
