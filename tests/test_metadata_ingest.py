import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import yaml

from scripts import metadata_ingest, openmetadata_bootstrap

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    "OPENMETADATA_HOST": "http://omd:8585/api",
    "OPENMETADATA_JWT": "jwt",
    "OPENMETADATA_SERVICE": "supabase",
    "PGHOST": "db.example",
    "PGPORT": "6543",
    "PGUSER": "dbt",
    "PGPASSWORD": "secret",
    "PGDATABASE": "postgres",
    "PGSSLMODE": "require",
    "DBT_SCHEMA": "analytics",
}


class WorkflowConfigTests(unittest.TestCase):
    def test_database_workflow_covers_landing_and_dbt_schemas_with_ddl(self):
        with patch.dict(os.environ, ENV, clear=True):
            cfg = metadata_ingest.database_config()
        conn = cfg["source"]["serviceConnection"]["config"]
        source = cfg["source"]["sourceConfig"]["config"]
        self.assertEqual(conn["hostPort"], "db.example:6543")
        self.assertEqual(conn["username"], "dbt")
        self.assertEqual(conn["sslMode"], "require")
        self.assertTrue(source["includeViews"] and source["includeDDL"])
        patterns = source["schemaFilterPattern"]["includes"]
        self.assertIn("^landing_web_analytics$", patterns)
        self.assertRegex("analytics_platinum", patterns[1])
        self.assertRegex("analytics_history", patterns[1])
        self.assertNotRegex("analytics_ci", patterns[1])

    def test_database_workflow_prefers_catalog_user(self):
        env = {**ENV, "OPENMETADATA_PGUSER": "catalog", "OPENMETADATA_PGPASSWORD": "ro"}
        with patch.dict(os.environ, env, clear=True):
            conn = metadata_ingest.database_config()["source"]["serviceConnection"]
        self.assertEqual(conn["config"]["username"], "catalog")
        self.assertEqual(conn["config"]["authType"], {"password": "ro"})

    def test_full_dbt_workflow_updates_docs_owners_and_tags(self):
        with patch.dict(os.environ, ENV, clear=True):
            cfg = metadata_ingest.dbt_config("full", "unused")
        source = cfg["source"]["sourceConfig"]["config"]
        self.assertTrue(source["dbtUpdateDescriptions"])
        self.assertTrue(source["dbtUpdateOwners"])
        self.assertTrue(source["includeTags"])
        self.assertNotIn("tableFilterPattern", source)
        self.assertTrue(
            source["dbtConfigSource"]["dbtRunResultsFilePath"].endswith(
                "run_results.json"
            )
        )

    def test_slim_dbt_workflow_filters_to_selection_or_skips(self):
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(
                metadata_ingest, "changed_tables", return_value=["^fct_orders$"]
            ),
        ):
            cfg = metadata_ingest.dbt_config("slim", "state")
        self.assertEqual(
            cfg["source"]["sourceConfig"]["config"]["tableFilterPattern"],
            {"includes": ["^fct_orders$"]},
        )
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(metadata_ingest, "changed_tables", return_value=[]),
        ):
            self.assertIsNone(metadata_ingest.dbt_config("slim", "state"))

    def test_main_runs_bootstrap_then_database_then_dbt(self):
        calls = []
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(
                metadata_ingest.openmetadata_bootstrap,
                "bootstrap",
                side_effect=lambda *a: calls.append("bootstrap"),
            ),
            patch.object(
                metadata_ingest,
                "run_workflow",
                side_effect=lambda w: calls.append(w["source"]["type"]),
            ),
        ):
            metadata_ingest.main("full", "state")
        self.assertEqual(calls, ["bootstrap", "postgres", "dbt"])


class BootstrapTests(unittest.TestCase):
    def test_creates_every_entity_with_put(self):
        session = MagicMock()
        session.headers = {}
        session.put.return_value.status_code = 200
        session.put.return_value.json.return_value = {"id": "team-id"}
        client = openmetadata_bootstrap.Client("http://omd/api/", "jwt", session)
        openmetadata_bootstrap.bootstrap(client, "https://grafana.example")
        urls = [c.args[0] for c in session.put.call_args_list]
        bodies = [c.kwargs["json"] for c in session.put.call_args_list]
        self.assertEqual(urls[0], "http://omd/api/v1/teams")
        self.assertEqual(session.headers["Authorization"], "Bearer jwt")
        self.assertEqual(
            urls.count("http://omd/api/v1/domains"), len(openmetadata_bootstrap.DOMAINS)
        )
        dashboard = bodies[urls.index("http://omd/api/v1/dashboards")]
        self.assertEqual(
            dashboard["sourceUrl"], "https://grafana.example/d/web-analytics"
        )
        self.assertEqual(dashboard["owners"], [{"id": "team-id", "type": "team"}])

    def test_http_error_fails_loudly(self):
        session = MagicMock()
        session.headers = {}
        session.put.return_value.status_code = 401
        session.put.return_value.text = "unauthorized"
        client = openmetadata_bootstrap.Client("http://omd/api", "bad", session)
        with self.assertRaisesRegex(RuntimeError, "401"):
            openmetadata_bootstrap.bootstrap(client)


class DeclaredMetadataTests(unittest.TestCase):
    """Every name dbt meta points at must be created by the bootstrap."""

    def test_dbt_meta_references_exist_in_bootstrap(self):
        domains, glossary, tags, owners = set(), set(), set(), set()

        def walk(node):
            if isinstance(node, dict):
                om = node.get("openmetadata")
                if isinstance(om, dict):
                    if om.get("domain"):
                        domains.add(om["domain"])
                    glossary.update(om.get("glossary", []))
                    tags.update(om.get("tags", []))
                if isinstance(node.get("owner"), str):
                    owners.add(node["owner"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        files = [ROOT / "dbt/dbt_project.yml", *ROOT.glob("dbt/**/*.yml")]
        for path in files:
            if "target" not in path.parts and "dbt_packages" not in path.parts:
                walk(yaml.safe_load(path.read_text()))
        boot = openmetadata_bootstrap
        self.assertTrue(domains)
        self.assertLessEqual(domains, set(boot.DOMAINS))
        self.assertLessEqual(
            glossary, {f"{boot.GLOSSARY['name']}.{t}" for t in boot.TERMS}
        )
        self.assertLessEqual(
            tags,
            {f"{boot.CLASSIFICATION['name']}.{t}" for t in boot.SENSITIVITY_TAGS},
        )
        self.assertEqual(owners, {boot.TEAM["name"]})


if __name__ == "__main__":
    unittest.main()
