"""Idempotently create the governance entities that dbt `meta` refers to.

dbt ingestion only *links* owners, domains, glossary terms and tags; it never
creates them, and silently skips names it cannot resolve. Running this before
ingestion keeps the catalog and the dbt declarations in sync. Every call is a
PUT (create-or-update), so re-running is safe.
"""

from __future__ import annotations

import os

import requests

TEAM = {
    "name": "analytics-engineering",
    "displayName": "Analytics Engineering",
    "teamType": "Group",
    "description": "Owns the web analytics pipeline, dbt models and marts.",
}

# dbt meta.openmetadata.domain values -> (domainType, description)
DOMAINS = {
    "WebAnalyticsSource": (
        "Source-aligned",
        "Landing, bronze and silver copies of the Xomdata web_analytics source.",
    ),
    "Acquisition": ("Aggregate", "Sessions and traffic channels (UTM, referrer)."),
    "Engagement": ("Aggregate", "Pageviews, landing pages and the ordered funnel."),
    "Commerce": ("Aggregate", "Orders and order items."),
    "Finance": ("Consumer-aligned", "Refunds and daily revenue/profit reporting."),
    "Customer": ("Aggregate", "Customers and purchase cohorts."),
    "Product": ("Aggregate", "Product catalog, observed history and daily sales."),
    "Shared": ("Aggregate", "Conformed calendar and device dimensions."),
    "Marketing": ("Consumer-aligned", "Daily channel performance and conversion."),
}

GLOSSARY = {
    "name": "WebAnalytics",
    "displayName": "Web Analytics",
    "description": "Business terms used by the web analytics marts.",
}

TERMS = {
    "Session": "One visit to the website; starts at the first pageview.",
    "Pageview": "One page load within a session.",
    "Order": "A purchase placed in a session; may contain several items.",
    "OrderItem": "One unit of one product within an order.",
    "Refund": "A refund event for one order item; an item can be refunded more than once.",
    "GrossRevenue": "Order or item price in USD before refunds.",
    "NetRevenue": "Gross revenue minus refunds in USD; can be negative on refund-only days.",
    "SessionConversionRate": "Sessions with at least one order divided by all sessions.",
}

CLASSIFICATION = {
    "name": "Sensitivity",
    "description": "Data sensitivity level used for access reviews.",
    "mutuallyExclusive": True,
}

# Grafana dashboards declared as dbt exposures. Names are Grafana UIDs, which is
# also how the OpenMetadata Grafana connector names dashboards, so a later run of
# that connector updates these entities instead of duplicating them.
DASHBOARD_SERVICE = {"name": "grafana", "serviceType": "Grafana"}
DASHBOARDS = {
    "web-analytics": (
        "Web Analytics",
        "Revenue and refunds, session conversion rate and ordered funnel.",
    ),
}

SENSITIVITY_TAGS = {
    "Public": "Safe to publish.",
    "Internal": "Internal use only.",
    "Confidential": "Pseudonymous identifiers and other restricted data.",
    "PII": "Directly identifies a person.",
}


class Client:
    def __init__(self, host: str, token: str, session: requests.Session | None = None):
        self.base = host.rstrip("/") + "/v1"
        self.session = session or requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def put(self, path: str, body: dict) -> dict:
        response = self.session.put(f"{self.base}/{path}", json=body, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(
                f"PUT {path} {body.get('name')}: {response.status_code} {response.text[:300]}"
            )
        return response.json()


def bootstrap(client: Client, grafana_url: str = "http://localhost:3000") -> None:
    team = client.put("teams", TEAM)
    owners = [{"id": team["id"], "type": "team"}]
    for name, (domain_type, description) in DOMAINS.items():
        client.put(
            "domains",
            {
                "name": name,
                "domainType": domain_type,
                "description": description,
                "owners": owners,
            },
        )
    client.put("glossaries", {**GLOSSARY, "owners": owners})
    for name, description in TERMS.items():
        client.put(
            "glossaryTerms",
            {"glossary": GLOSSARY["name"], "name": name, "description": description},
        )
    client.put("classifications", CLASSIFICATION)
    for name, description in SENSITIVITY_TAGS.items():
        client.put(
            "tags",
            {
                "classification": CLASSIFICATION["name"],
                "name": name,
                "description": description,
            },
        )
    client.put("services/dashboardServices", DASHBOARD_SERVICE)
    for uid, (title, description) in DASHBOARDS.items():
        client.put(
            "dashboards",
            {
                "name": uid,
                "displayName": title,
                "description": description,
                "service": DASHBOARD_SERVICE["name"],
                "sourceUrl": f"{grafana_url.rstrip('/')}/d/{uid}",
                "owners": owners,
            },
        )


if __name__ == "__main__":
    bootstrap(
        Client(os.environ["OPENMETADATA_HOST"], os.environ["OPENMETADATA_JWT"]),
        os.getenv("GRAFANA_URL", "http://localhost:3000"),
    )
    print("OpenMetadata governance entities are up to date.")
