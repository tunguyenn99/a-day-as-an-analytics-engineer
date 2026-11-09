"""OpenMetadata ingestion for CD: governance bootstrap -> database metadata -> dbt.

1. Bootstrap: create the team, domains, glossary and tags that dbt `meta` links to.
2. Database metadata: register every landing/analytics schema, table and view
   (with DDL) so tables built by this deploy exist before dbt is ingested; dbt
   ingestion skips models whose table is unknown to the catalog.
3. dbt: descriptions, owners, domains, tiers, glossary terms, tags, lineage,
   raw + compiled SQL, and test results, from the complete manifest/catalog.

Slim mode limits step 3 to the CD selection (state:modified+); steps 1-2 always
run in full because they are cheap and keep the catalog consistent.
"""

import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

import yaml

from scripts import openmetadata_bootstrap


def server_config():
    return {
        "loggerLevel": "INFO",
        "openMetadataServerConfig": {
            "hostPort": os.environ["OPENMETADATA_HOST"],
            "authProvider": "openmetadata",
            "securityConfig": {"jwtToken": os.environ["OPENMETADATA_JWT"]},
        },
    }


def schema_patterns():
    base = re.escape(os.getenv("DBT_SCHEMA", "analytics"))
    return [
        "^landing_web_analytics$",
        f"^{base}_(bronze|silver|gold|platinum|history)$",
    ]


def database_config():
    """PostgreSQL metadata workflow; prefer a dedicated read-only catalog user."""
    return {
        "source": {
            "type": "postgres",
            "serviceName": os.environ["OPENMETADATA_SERVICE"],
            "serviceConnection": {
                "config": {
                    "type": "Postgres",
                    "hostPort": f"{os.environ['PGHOST']}:{os.getenv('PGPORT', '5432')}",
                    "username": os.getenv("OPENMETADATA_PGUSER")
                    or os.environ["PGUSER"],
                    "authType": {
                        "password": os.getenv("OPENMETADATA_PGPASSWORD")
                        or os.environ["PGPASSWORD"]
                    },
                    "database": os.environ["PGDATABASE"],
                    "sslMode": os.getenv("PGSSLMODE", "require"),
                }
            },
            "sourceConfig": {
                "config": {
                    "type": "DatabaseMetadata",
                    "includeTables": True,
                    "includeViews": True,
                    "includeDDL": True,
                    "includeTags": True,
                    "markDeletedTables": True,
                    "schemaFilterPattern": {"includes": schema_patterns()},
                }
            },
        },
        "sink": {"type": "metadata-rest", "config": {}},
        "workflowConfig": server_config(),
    }


def changed_tables(state):
    """Table-name regexes for the same graph selector CD built."""
    proc = subprocess.run(
        [
            "dbt",
            "--quiet",
            "ls",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "dbt",
            "--target",
            "prod",
            "--select",
            "state:modified+",
            "--state",
            state,
            "--output",
            "json",
            "--resource-type",
            "model",
            "snapshot",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    selected = [
        json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")
    ]
    return ["^" + re.escape(n.get("alias") or n["name"]) + "$" for n in selected]


def dbt_config(mode, state):
    target = Path("dbt/target").resolve()
    names = []
    if mode == "slim":
        names = changed_tables(state)
        if not names:
            return None
    return {
        "source": {
            "type": "dbt",
            "serviceName": os.environ["OPENMETADATA_SERVICE"],
            "sourceConfig": {
                "config": {
                    "type": "DBT",
                    "dbtConfigSource": {
                        "dbtConfigType": "local",
                        "dbtManifestFilePath": str(target / "manifest.json"),
                        "dbtCatalogFilePath": str(target / "catalog.json"),
                        "dbtRunResultsFilePath": str(target / "run_results.json"),
                    },
                    # dbt YAML is the source of truth for docs and ownership.
                    "dbtUpdateDescriptions": True,
                    "dbtUpdateOwners": True,
                    "includeTags": True,
                    "dbtClassificationName": "dbtTags",
                    **({"tableFilterPattern": {"includes": names}} if names else {}),
                }
            },
        },
        "sink": {"type": "metadata-rest", "config": {}},
        "workflowConfig": server_config(),
    }


def run_workflow(workflow):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "workflow.yml"
        path.write_text(yaml.safe_dump(workflow))
        path.chmod(0o600)
        subprocess.run(
            [os.getenv("METADATA_BIN", "metadata"), "ingest", "-c", str(path)],
            check=True,
        )


def main(mode, state):
    openmetadata_bootstrap.bootstrap(
        openmetadata_bootstrap.Client(
            os.environ["OPENMETADATA_HOST"], os.environ["OPENMETADATA_JWT"]
        ),
        os.getenv("GRAFANA_URL", "http://localhost:3000"),
    )
    run_workflow(database_config())
    workflow = dbt_config(mode, state)
    if workflow:
        run_workflow(workflow)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["slim", "full"], required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()
    main(args.mode, args.state)
