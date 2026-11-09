import json
import os
from pathlib import Path
import unittest

import psycopg

from ingestion.web_analytics import publish


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1", "Requires disposable PostgreSQL warehouse"
)
class LandingTransactionTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads(Path("sample_data/web_analytics.json").read_text())
        with psycopg.connect("") as conn:
            publish(conn, lambda table: [self.rows[table]])

    def test_partial_extraction_failure_preserves_published_snapshot(self):
        with psycopg.connect("") as conn:
            before = conn.execute(
                "select extraction_id, payload from landing_web_analytics.website_sessions order by source_record_id"
            ).fetchall()

        def batches(table):
            if table == "products":
                return [[{"product_id": None}]]
            rows = self.rows[table]
            if table == "website_sessions":
                rows = [row | {"user_id": 9999} for row in rows]
            return [rows]

        with self.assertRaises(ValueError):
            with psycopg.connect("") as conn:
                publish(conn, batches)
        with psycopg.connect("") as conn:
            after = conn.execute(
                "select extraction_id, payload from landing_web_analytics.website_sessions order by source_record_id"
            ).fetchall()
        self.assertEqual(before, after)

    def test_replay_keeps_one_record_per_source_id(self):
        with psycopg.connect("") as conn:
            publish(conn, lambda table: [self.rows[table]])
        with psycopg.connect("") as conn:
            count = conn.execute(
                "select count(*) from landing_web_analytics.website_sessions"
            ).fetchone()[0]
        self.assertEqual(count, len(self.rows["website_sessions"]))
