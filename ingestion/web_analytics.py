"""Full SQL Server extraction with bounded-memory batches and atomic landing publish."""

import argparse
from datetime import date, datetime
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

import boto3
import psycopg
from psycopg import sql
import pymssql

SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text())

# Catalog documentation for landing; OpenMetadata reads Postgres comments.
LANDING_COLUMNS = {
    "source_record_id": "Primary key of the source row (the SQL Server table's ID column).",
    "record_hash": "SHA-256 of the serialized JSON payload; changes when any source attribute changes.",
    "payload": "Full source row as JSONB; decimals are serialized as strings to keep precision.",
    "ingested_at": "Load timestamp of the row (transaction time of the publishing load).",
    "extraction_id": "Full extraction run ID; joins to ingestion_runs and the S3 raw batch prefix.",
}
RUNS_COMMENTS = {
    None: "One row per published full extraction of the web_analytics source.",
    "extraction_id": "Extraction run ID; also the S3 raw batch prefix.",
    "published_at": "When the landing transaction published this extraction.",
    "row_counts": "Rows extracted per source table, as JSON.",
    "archived": "True if raw batches were archived to S3 for this run.",
}
BATCH_SIZE = 10000


def storage():
    return boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT_URL"])


def encode(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Unsupported source type {type(value).__name__}")


def serialize(table, row):
    if set(row) != set(SCHEMA[table]):
        raise ValueError(f"Source contract mismatch for {table}")
    key = next(iter(SCHEMA[table]))
    if not isinstance(row[key], int) or isinstance(row[key], bool):
        raise ValueError(f"Invalid natural key for {table}")
    body = json.dumps(
        row, default=encode, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return row[key], hashlib.sha256(body.encode()).hexdigest(), body


def source_connection():
    return pymssql.connect(
        server=os.environ["MSSQL_HOST"],
        port=int(os.getenv("MSSQL_PORT", "1433")),
        user=os.environ["MSSQL_USER"],
        password=os.environ["MSSQL_PASSWORD"],
        database=os.getenv("MSSQL_DATABASE", "xomdata_dataset"),
        login_timeout=15,
        timeout=120,
        as_dict=True,
        autocommit=True,
    )


def remote_batches(source, table):
    schema = os.getenv("MSSQL_SCHEMA", "web_analytics")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ValueError("Invalid MSSQL schema identifier")
    key = next(iter(SCHEMA[table]))
    columns = ", ".join(f"[{column}]" for column in SCHEMA[table])
    with source.cursor() as cursor:
        cursor.execute(
            f"SELECT MAX([{key}]) AS max_id, COUNT_BIG(*) AS row_count FROM [{schema}].[{table}]"
        )
        bounds = cursor.fetchone()
        maximum = bounds["max_id"]
        expected = bounds["row_count"]
        last_key = -1
        seen = 0
        while maximum is not None and last_key < maximum:
            cursor.execute(
                f"SELECT TOP ({BATCH_SIZE}) {columns} FROM [{schema}].[{table}] "
                f"WHERE [{key}] > %s AND [{key}] <= %s ORDER BY [{key}]",
                (last_key, maximum),
            )
            rows = cursor.fetchall()
            if not rows:
                break
            last_key = rows[-1][key]
            seen += len(rows)
            yield rows
        if seen != expected:
            raise ValueError(
                f"Extraction count changed for {table}; publication aborted"
            )


def comment(conn, table, comments):
    """COMMENT ON is transactional, so docs publish together with the data."""
    for column, text in comments.items():
        target = (
            sql.SQL("TABLE landing_web_analytics.{}").format(sql.Identifier(table))
            if column is None
            else sql.SQL("COLUMN landing_web_analytics.{}.{}").format(
                sql.Identifier(table), sql.Identifier(column)
            )
        )
        conn.execute(sql.SQL("COMMENT ON {} IS {}").format(target, sql.Literal(text)))


def publish(conn, batches_for, archive_client=None, bucket=None):
    """One DB transaction publishes all six tables or rolls back all changes."""
    conn.execute("SELECT pg_advisory_xact_lock(74329101)")
    extraction_id = uuid4().hex
    counts = {}
    conn.execute("CREATE SCHEMA IF NOT EXISTS landing_web_analytics")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS landing_web_analytics.ingestion_runs (
        extraction_id text primary key, published_at timestamptz default now(),
        row_counts jsonb not null, archived boolean not null)"""
    )
    for table in SCHEMA:
        stage = "stage_" + table
        conn.execute(
            sql.SQL(
                """CREATE TEMP TABLE {} (
            source_record_id bigint primary key, record_hash text not null,
            payload jsonb not null, ingested_at timestamptz not null default now(),
            extraction_id text not null) ON COMMIT DROP"""
            ).format(sql.Identifier(stage))
        )
        count = 0
        for batch_number, rows in enumerate(batches_for(table)):
            records = [serialize(table, row) for row in rows]
            if archive_client is not None:
                body = gzip.compress(
                    ("\n".join(record[2] for record in records) + "\n").encode(),
                    mtime=0,
                )
                archive_client.put_object(
                    Bucket=bucket,
                    Key=f"raw/web_analytics/{extraction_id}/{table}/{batch_number:06d}.jsonl.gz",
                    Body=body,
                    ContentType="application/gzip",
                )
            with (
                conn.cursor() as cur,
                cur.copy(
                    sql.SQL(
                        "COPY {} (source_record_id, record_hash, payload, extraction_id) FROM STDIN"
                    ).format(sql.Identifier(stage))
                ) as copy,
            ):
                for key, digest, body in records:
                    copy.write_row((key, digest, body, extraction_id))
            count += len(records)
        counts[table] = count
        # Stable table identities keep downstream dbt view dependencies intact.
        conn.execute(
            sql.SQL(
                "CREATE TABLE IF NOT EXISTS landing_web_analytics.{} (LIKE {} INCLUDING ALL)"
            ).format(sql.Identifier(table), sql.Identifier(stage))
        )
        conn.execute(
            sql.SQL("TRUNCATE TABLE landing_web_analytics.{}").format(
                sql.Identifier(table)
            )
        )
        conn.execute(
            sql.SQL("INSERT INTO landing_web_analytics.{} SELECT * FROM {}").format(
                sql.Identifier(table), sql.Identifier(stage)
            )
        )
        comment(
            conn,
            table,
            {
                None: f"Current full extraction of web_analytics.{table}.",
                **LANDING_COLUMNS,
            },
        )
        print(
            json.dumps({"table": table, "rows": count, "extraction_id": extraction_id}),
            flush=True,
        )
    comment(conn, "ingestion_runs", RUNS_COMMENTS)
    conn.execute(
        "INSERT INTO landing_web_analytics.ingestion_runs (extraction_id, row_counts, archived) VALUES (%s, %s, %s)",
        (extraction_id, json.dumps(counts), archive_client is not None),
    )
    return extraction_id, counts


def ingest(fixture=False, archive=True):
    client = storage() if archive else None
    bucket = os.environ["S3_BUCKET"] if archive else None
    if fixture:
        rows = json.loads(
            (
                Path(__file__).resolve().parents[1] / "sample_data/web_analytics.json"
            ).read_text()
        )
        with psycopg.connect("") as conn:
            extraction_id, counts = publish(
                conn, lambda table: [rows[table]], client, bucket
            )
    else:
        with source_connection() as source, psycopg.connect("") as conn:
            extraction_id, counts = publish(
                conn, lambda table: remote_batches(source, table), client, bucket
            )
    # Completion marker follows DB commit. Failed raw batches have no completion marker.
    if client is not None:
        client.put_object(
            Bucket=bucket,
            Key=f"raw/web_analytics/{extraction_id}/complete.json",
            Body=json.dumps(
                {"extraction_id": extraction_id, "row_counts": counts}
            ).encode(),
            ContentType="application/json",
        )
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture", action="store_true", help="Use synthetic offline fixture"
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Explicitly skip S3 for local validation",
    )
    args = parser.parse_args()
    ingest(fixture=args.fixture, archive=not args.no_archive)
