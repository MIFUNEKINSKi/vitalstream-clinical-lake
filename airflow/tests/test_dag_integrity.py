"""DAG integrity test: every DAG in airflow/dags imports cleanly.

Run in CI (Linux) with apache-airflow installed; Airflow does not support
Windows, so this is not part of the main pytest suite.
"""

import os

from airflow.models import DagBag

DAG_DIR = os.path.join(os.path.dirname(__file__), "..", "dags")


def test_dags_import_without_errors():
    bag = DagBag(dag_folder=DAG_DIR, include_examples=False)
    assert bag.import_errors == {}, f"DAG import errors: {bag.import_errors}"


def test_vitalstream_dag_structure():
    bag = DagBag(dag_folder=DAG_DIR, include_examples=False)
    dag = bag.dags["vitalstream_dbt_pipeline"]

    task_ids = [t.task_id for t in dag.topological_sort()]
    assert task_ids == ["generate_seed", "dbt_seed", "dbt_run", "dbt_test", "dbt_docs"]
    assert dag.schedule_interval is not None
    assert dag.catchup is False
