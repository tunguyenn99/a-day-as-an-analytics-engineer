from datetime import datetime
import json
import unittest

from ingestion.web_analytics import serialize


class SourceContractTests(unittest.TestCase):
    def test_decimal_and_datetime_preserve_source_values(self):
        row = dict(product_id=1, created_at=datetime(2015, 1, 1), product_name="Bear")
        key, digest, body = serialize("products", row)
        self.assertEqual(key, 1)
        self.assertEqual(json.loads(body)["created_at"], "2015-01-01T00:00:00")
        self.assertEqual(
            digest, serialize("products", dict(reversed(list(row.items()))))[1]
        )

    def test_rejects_missing_or_unexpected_columns(self):
        for row in (
            {"product_id": 1},
            {"product_id": 1, "created_at": None, "product_name": "Bear", "extra": 1},
        ):
            with self.assertRaises(ValueError):
                serialize("products", row)

    def test_rejects_invalid_primary_key(self):
        for value in (None, "1", True):
            with self.assertRaises(ValueError):
                serialize(
                    "products",
                    dict(product_id=value, created_at=None, product_name="Bear"),
                )
