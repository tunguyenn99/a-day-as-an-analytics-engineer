with cohorts as (
    select
        user_id,
        date_trunc('month', first_order_at)::date as cohort_month
    from {{ ref('dim_customer') }}
    where first_order_at is not null
),

cohort_sizes as (
    select
        cohort_month,
        count(*) as cohort_customers
    from cohorts
    group by cohort_month
),

activity as (
    select
        c.cohort_month,
        date_trunc('month', o.ordered_at)::date as activity_month,
        count(distinct o.user_id) as purchasing_customers,
        count(*) as orders,
        sum(o.gross_revenue_usd) as gross_revenue_usd
    from cohorts as c inner join {{ ref('fct_orders') }} as o on c.user_id = o.user_id
    group by c.cohort_month, date_trunc('month', o.ordered_at)::date
)

select
    a.cohort_month,
    a.activity_month,
    cs.cohort_customers,
    a.purchasing_customers,
    a.orders,
    a.gross_revenue_usd,
    (extract(year from a.activity_month)::integer - extract(year from a.cohort_month)::integer) * 12
    + extract(month from a.activity_month)::integer - extract(month from a.cohort_month)::integer
    as months_since_first_order,
    sum(a.gross_revenue_usd) over (
        partition by a.cohort_month
        order by a.activity_month
        rows between unbounded preceding and current row
    ) / nullif(cs.cohort_customers, 0) as cumulative_gross_ltv_usd
from activity as a inner join cohort_sizes as cs on a.cohort_month = cs.cohort_month
