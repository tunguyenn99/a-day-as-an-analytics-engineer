import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dags"))

import callbacks  # noqa: E402


def context(error="boom"):
    ti = SimpleNamespace(
        dag_id="web_analytics_medallion",
        task_id="ingest_sources",
        try_number=3,
        log_url="http://airflow/log",
    )
    return {"task_instance": ti, "run_id": "scheduled__2026", "exception": error}


class FailureCallbackTests(unittest.TestCase):
    def test_message_names_task_run_error_and_log(self):
        message = callbacks.failure_message(context())
        self.assertIn("web_analytics_medallion.ingest_sources", message)
        self.assertIn("scheduled__2026", message)
        self.assertIn("error: boom", message)
        self.assertIn("http://airflow/log", message)

    def test_without_webhook_only_logs(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(callbacks.urllib.request, "urlopen") as urlopen,
        ):
            callbacks.notify_failure(context())
        urlopen.assert_not_called()

    def test_posts_slack_compatible_json(self):
        with (
            patch.dict(os.environ, {"ALERT_WEBHOOK_URL": "https://hook"}),
            patch.object(callbacks.urllib.request, "urlopen") as urlopen,
        ):
            urlopen.return_value.__enter__.return_value = MagicMock()
            callbacks.notify_failure(context())
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://hook")
        self.assertIn("ingest_sources", json.loads(request.data)["text"])

    def test_delivery_error_does_not_raise(self):
        with (
            patch.dict(os.environ, {"ALERT_WEBHOOK_URL": "https://hook"}),
            patch.object(
                callbacks.urllib.request, "urlopen", side_effect=OSError("down")
            ),
            self.assertLogs(callbacks.log, "ERROR"),
        ):
            callbacks.notify_failure(context())


if __name__ == "__main__":
    unittest.main()
