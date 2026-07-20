"""Airflow DAG: scheduled dbt build + data-quality tests for VitalStream.

Orchestrates the analytics layer on a weekly schedule:

    generate_seed -> dbt_seed -> dbt_run -> dbt_test -> dbt_docs

The seed is regenerated from vocabulary.py first so the dbt reference data
can never drift from the pipeline's single source of truth. dbt_test runs
the schema + singular tests that mirror the PySpark DQ checks, and a test
failure fails the DAG run.

Point VITALSTREAM_REPO_ROOT at the repo checkout on the Airflow worker
(defaults to /opt/airflow/vitalstream). Targets the duckdb dev profile by
default; set DBT_TARGET=athena on a worker with AWS credentials to run
against the deployed curated zone.
"""

import os
from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator

from airflow import DAG

REPO_ROOT = os.environ.get("VITALSTREAM_REPO_ROOT", "/opt/airflow/vitalstream")
DBT_DIR = os.path.join(REPO_ROOT, "dbt")
DBT_TARGET = os.environ.get("DBT_TARGET", "dev")

default_args = {
    "owner": "vitalstream",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="vitalstream_dbt_pipeline",
    description="Weekly dbt build + DQ tests over the curated OMOP tables",
    schedule="@weekly",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args=default_args,
    tags=["vitalstream", "dbt", "omop", "data-quality"],
    doc_md=__doc__,
) as dag:
    generate_seed = BashOperator(
        task_id="generate_seed",
        bash_command="python scripts/generate_dbt_seed.py",
        cwd=REPO_ROOT,
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"dbt seed --target {DBT_TARGET}",
        cwd=DBT_DIR,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"dbt run --target {DBT_TARGET}",
        cwd=DBT_DIR,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"dbt test --target {DBT_TARGET}",
        cwd=DBT_DIR,
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs",
        bash_command=f"dbt docs generate --target {DBT_TARGET}",
        cwd=DBT_DIR,
    )

    generate_seed >> dbt_seed >> dbt_run >> dbt_test >> dbt_docs
