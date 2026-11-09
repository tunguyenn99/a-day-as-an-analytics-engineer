"""Serialized CD: use immutable baseline; promote pointer only after metadata succeeds."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from ingestion.web_analytics import storage

ROOT = Path(__file__).resolve().parents[1]


def dbt(*args):
    subprocess.run(
        [
            "dbt",
            *args,
            "--project-dir",
            str(ROOT / "dbt"),
            "--profiles-dir",
            str(ROOT / "dbt"),
            "--target",
            "prod",
        ],
        check=True,
    )


def main(mode):
    s3 = storage()
    bucket = os.environ["S3_BUCKET"]
    state = ROOT / ".state" / uuid4().hex
    state.mkdir(parents=True)
    flags = []
    if mode == "slim":
        # Missing state is an error. Bootstrap deliberately with manual full CD.
        pointer = json.loads(
            s3.get_object(Bucket=bucket, Key="production/latest.json")["Body"].read()
        )
        s3.download_file(
            bucket, pointer["prefix"] + "/manifest.json", str(state / "manifest.json")
        )
        flags = ["--select", "state:modified+", "--state", str(state), "--defer"]
    dbt("deps")
    dbt("compile", *flags)
    dbt("build", *flags)
    # build includes tests; explicit test phase also checks requested CD contract.
    dbt("test", *flags)
    results = json.loads((ROOT / "dbt/target/run_results.json").read_text())
    changed = [r["unique_id"] for r in results["results"]]
    # docs generate creates the complete manifest/catalog; never prune lineage artifacts.
    dbt("docs", "generate")
    # Preserve the test execution artifact if a later dbt command replaces it.
    (ROOT / "dbt/target/run_results.json").write_text(json.dumps(results))
    prefix = "production/runs/" + uuid4().hex
    for name in ("manifest.json", "catalog.json", "run_results.json"):
        s3.upload_file(str(ROOT / "dbt/target" / name), bucket, prefix + "/" + name)
    (ROOT / "dbt/target/selection.json").write_text(
        json.dumps({"mode": mode, "tested_nodes": changed})
    )
    s3.upload_file(
        str(ROOT / "dbt/target/selection.json"), bucket, prefix + "/selection.json"
    )
    subprocess.run(
        [
            "python",
            "-m",
            "scripts.metadata_ingest",
            "--mode",
            mode,
            "--state",
            str(state),
        ],
        check=True,
    )
    s3.put_object(
        Bucket=bucket,
        Key="production/latest.json",
        Body=json.dumps({"prefix": prefix}).encode(),
        ContentType="application/json",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["slim", "full"], required=True)
    main(parser.parse_args().mode)
