import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import deploy


class PromotionTests(unittest.TestCase):
    def run_release(self, failure):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "dbt/target"
            target.mkdir(parents=True)
            for name, payload in [
                ("manifest", {}),
                ("catalog", {}),
                ("run_results", {"results": []}),
            ]:
                (target / f"{name}.json").write_text(json.dumps(payload))
            with (
                patch.object(deploy, "ROOT", root),
                patch.object(deploy, "storage") as storage,
                patch.object(deploy, "dbt") as dbt,
                patch.object(deploy.subprocess, "run") as metadata,
                patch.dict(os.environ, {"S3_BUCKET": "test"}),
            ):
                if failure == "build":

                    def command(*args):
                        if args[0] == "build":
                            raise subprocess.CalledProcessError(1, "dbt build")

                    dbt.side_effect = command
                if failure == "metadata":
                    metadata.side_effect = subprocess.CalledProcessError(
                        1, "metadata ingest"
                    )
                if failure:
                    with self.assertRaises(subprocess.CalledProcessError):
                        deploy.main("full")
                    storage.return_value.put_object.assert_not_called()
                else:
                    deploy.main("full")
                    self.assertEqual(
                        storage.return_value.put_object.call_args.kwargs["Key"],
                        "production/latest.json",
                    )

    def test_build_failure_does_not_promote(self):
        self.run_release("build")

    def test_metadata_failure_does_not_promote(self):
        self.run_release("metadata")

    def test_success_promotes(self):
        self.run_release(None)
