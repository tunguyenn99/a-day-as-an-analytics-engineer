import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import LoadMode, TestBehavior

from callbacks import notify_failure
from ingestion.web_analytics import ingest

PROJECT = Path(os.getenv("DBT_PROJECT_DIR", "/opt/airflow/project/dbt"))
DBT = os.getenv("DBT_EXECUTABLE_PATH", "/opt/airflow/dbt-venv/bin/dbt")

with DAG(
    "web_analytics_medallion",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "on_failure_callback": notify_failure,
    },
    dagrun_timeout=timedelta(hours=3),
) as dag:
    raw = PythonOperator(
        task_id="ingest_sources",
        python_callable=ingest,
        op_kwargs={
            "fixture": os.getenv("INGESTION_MODE", "remote") == "fixture",
            "archive": os.getenv("INGESTION_ARCHIVE", "true").lower() == "true",
        },
    )
    models = DbtTaskGroup(
        group_id="medallion",
        project_config=ProjectConfig(dbt_project_path=PROJECT),
        profile_config=ProfileConfig(
            profile_name="analytics_engineering",
            target_name="prod",
            profiles_yml_filepath=PROJECT / "profiles.yml",
        ),
        execution_config=ExecutionConfig(dbt_executable_path=DBT),
        render_config=RenderConfig(
            dbt_executable_path=DBT,
            load_method=LoadMode.DBT_LS,
            test_behavior=TestBehavior.AFTER_ALL,
        ),
    )
    raw >> models
