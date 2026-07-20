# Airflow Orchestration

Scheduled orchestration for the VitalStream analytics layer. The
`vitalstream_dbt_pipeline` DAG runs weekly:

```
generate_seed → dbt_seed → dbt_run → dbt_test → dbt_docs
```

- **generate_seed** — regenerates the dbt reference seed from
  `vocabulary.py`, so dbt can never drift from the pipeline's single source
  of truth.
- **dbt_run / dbt_test** — builds the staging + marts models and runs the
  schema and singular tests that mirror the PySpark DQ checks; a failing
  test fails the DAG run.
- **dbt_docs** — refreshes the lineage/catalog docs.

The AWS pipeline itself (validate → Glue ETL → DQ → crawler) stays on Step
Functions — AWS-native orchestration with per-state error handling. Airflow
owns the recurring analytics build, which is the natural split: event-driven
ingestion on Step Functions, scheduled transformation on Airflow.

## Running locally

Airflow does not support Windows; use Linux, WSL, or Docker.

```bash
pip install "apache-airflow==2.10.5" dbt-duckdb
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export VITALSTREAM_REPO_ROOT=$(pwd)
airflow standalone          # webserver + scheduler at localhost:8080
```

Trigger `vitalstream_dbt_pipeline` from the UI, or run a single task:

```bash
airflow dags test vitalstream_dbt_pipeline 2026-07-20
```

By default the DAG targets the free duckdb profile over `sample_outputs/`;
set `DBT_TARGET=athena` (plus AWS credentials and
`DBT_ATHENA_S3_STAGING_DIR`) to run against the deployed curated zone.

## CI

`airflow/tests/test_dag_integrity.py` runs in CI on Linux: it imports the
DagBag and asserts the DAG parses cleanly with the expected task sequence.
