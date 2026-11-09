{% docs __overview__ %}
# Web Analytics Engineering

**Xóm Ecom Tracker · SQL Server → PostgreSQL · dbt + Airflow/Cosmos**

A medallion analytics project with **30 models**, **6 source tables**, and product SCD2 history.

## Data layers

| Layer | Models | Purpose |
| --- | --- | --- |
| Bronze | 6 | Source envelopes and extraction provenance |
| Silver | 6 | Typed entities and source quality checks |
| Gold | 12 | Domain facts and conformed dimensions |
| Platinum | 6 | Business data marts with explicit metric grains |

## Gold domains

Acquisition, Engagement, Commerce, Finance, Customer, Product and Shared.

Facts retain their atomic grains: **session, pageview, order, order item, refund**.
Dimensions cover channel, device, page, date, customer and product.

## Platinum data products

- **Marketing daily** — sessions, conversion, orders and revenue by channel/device.
- **Ordered funnel** — products → cart → shipping → billing → thank-you.
- **Landing-page daily** — entry page, bounce and conversion.
- **Finance daily** — event-date gross revenue, refunds and net revenue.
- **Product daily** — sales and observed refunds attributed to original sale date.
- **Customer cohorts** — first-order cohorts and cumulative gross LTV.

## Explore

Use **Project** to browse layers and domains, **Database** to browse warehouse schemas,
and the graph button to explore lineage. Every SQL model has an individual YAML file.

See the repository README, domain-modeling contracts and validation report for setup,
measured dataset totals and deployment limitations. Catalog content describes the
warehouse used when `dbt docs generate` was run; it does not prove a cloud deployment.
{% enddocs %}
