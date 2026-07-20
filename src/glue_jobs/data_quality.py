"""Data quality checks for OMOP CDM tables.

Runs null checks, range validation, and referential integrity checks.
Produces a structured JSON report with pass/fail per check.

Also the entry point for the standalone Glue DQ job (see infrastructure/glue.tf):
reads the curated OMOP Parquet tables, runs all checks, and writes the report
one row per check to {dq_output_path}/data_quality_report/ for Athena.
Per the pipeline design, a failing check does not fail the job — the report
records the violations.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, lit, when
from pyspark.sql.functions import sum as spark_sum
from pyspark.sql.types import (
    BooleanType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

from src.data_generator.vocabulary import VITAL_SIGNS

# Flattened one-row-per-check schema for the Athena data_quality_report table.
# Fields not applicable to a check type are null.
DQ_REPORT_ROW_SCHEMA = StructType([
    StructField("run_timestamp", StringType(), nullable=False),
    StructField("check_type", StringType(), nullable=False),
    StructField("table", StringType(), nullable=True),
    StructField("column", StringType(), nullable=True),
    StructField("measurement", StringType(), nullable=True),
    StructField("concept_id", IntegerType(), nullable=True),
    StructField("range", StringType(), nullable=True),
    StructField("relationship", StringType(), nullable=True),
    StructField("total_rows", LongType(), nullable=True),
    StructField("violations", LongType(), nullable=True),
    StructField("orphan_count", LongType(), nullable=True),
    StructField("passed", BooleanType(), nullable=False),
])


def run_null_checks(person_df: DataFrame, measurement_df: DataFrame, visit_df: DataFrame) -> list[dict]:
    """Check critical columns for unexpected nulls — one aggregation pass per table."""
    checks = []

    null_specs = [
        ("person", person_df, ["person_id", "gender_concept_id", "year_of_birth"]),
        ("measurement", measurement_df, ["measurement_id", "person_id", "measurement_date", "value_as_number"]),
        ("visit_occurrence", visit_df, ["visit_occurrence_id", "person_id", "visit_start_date"]),
    ]

    for table_name, df, columns in null_specs:
        agg_row = df.agg(
            count(lit(1)).alias("_total_rows"),
            *[
                spark_sum(when(col(c).isNull(), 1).otherwise(0)).alias(c)
                for c in columns
            ],
        ).first()
        total = agg_row["_total_rows"]
        for col_name in columns:
            null_count = agg_row[col_name] or 0
            checks.append({
                "check_type": "null_check",
                "table": table_name,
                "column": col_name,
                "total_rows": total,
                "violations": null_count,
                "passed": null_count == 0,
            })

    return checks


def run_range_checks(measurement_df: DataFrame) -> list[dict]:
    """Validate vital signs fall within the clinically plausible ranges
    defined on VITAL_SIGNS — a single groupBy pass over the table."""
    bounds = {vs.omop_concept_id: vs for vs in VITAL_SIGNS}

    out_of_range = lit(False)
    for concept_id, vs in bounds.items():
        out_of_range = out_of_range | (
            (col("measurement_concept_id") == concept_id)
            & ((col("value_as_number") < vs.min_plausible) | (col("value_as_number") > vs.max_plausible))
        )

    totals = {
        row["measurement_concept_id"]: row
        for row in (
            measurement_df
            .filter(col("measurement_concept_id").isin(list(bounds)))
            .groupBy("measurement_concept_id")
            .agg(
                count(lit(1)).alias("total_rows"),
                spark_sum(when(out_of_range, 1).otherwise(0)).alias("violations"),
            )
            .collect()
        )
    }

    checks = []
    for vs in VITAL_SIGNS:
        row = totals.get(vs.omop_concept_id)
        if row is None:
            continue

        violations = row["violations"] or 0
        checks.append({
            "check_type": "range_check",
            "measurement": vs.name,
            "concept_id": vs.omop_concept_id,
            "range": f"[{vs.min_plausible:g}, {vs.max_plausible:g}]",
            "total_rows": row["total_rows"],
            "violations": violations,
            "passed": violations == 0,
        })

    return checks


def run_referential_integrity_checks(
    person_df: DataFrame,
    visit_df: DataFrame,
    measurement_df: DataFrame,
) -> list[dict]:
    """Verify foreign key relationships between OMOP tables via anti-joins."""
    checks = []
    person_ids = person_df.select("person_id")

    ri_specs = [
        (
            "measurement.person_id → person.person_id",
            measurement_df.select("person_id"),
            person_ids,
            "person_id",
        ),
        (
            "visit_occurrence.person_id → person.person_id",
            visit_df.select("person_id"),
            person_ids,
            "person_id",
        ),
        (
            "measurement.visit_occurrence_id → visit_occurrence.visit_occurrence_id",
            measurement_df.filter(col("visit_occurrence_id").isNotNull()).select("visit_occurrence_id"),
            visit_df.select("visit_occurrence_id"),
            "visit_occurrence_id",
        ),
    ]

    for relationship, child_keys, parent_keys, key_col in ri_specs:
        orphan_count = child_keys.join(parent_keys, on=key_col, how="left_anti").count()
        checks.append({
            "check_type": "referential_integrity",
            "relationship": relationship,
            "orphan_count": orphan_count,
            "passed": orphan_count == 0,
        })

    return checks


def run_all_checks(
    person_df: DataFrame,
    visit_df: DataFrame,
    measurement_df: DataFrame,
) -> dict:
    """Run all DQ checks and return a structured report."""
    tables = (person_df, visit_df, measurement_df)
    for df in tables:
        df.cache()

    try:
        null_checks = run_null_checks(person_df, measurement_df, visit_df)
        range_checks = run_range_checks(measurement_df)
        ri_checks = run_referential_integrity_checks(person_df, visit_df, measurement_df)
    finally:
        for df in tables:
            df.unpersist()

    all_checks = null_checks + range_checks + ri_checks
    all_passed = all(c["passed"] for c in all_checks)

    return {
        "run_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "overall_result": "PASS" if all_passed else "FAIL",
        "total_checks": len(all_checks),
        "passed_checks": sum(1 for c in all_checks if c["passed"]),
        "failed_checks": sum(1 for c in all_checks if not c["passed"]),
        "checks": all_checks,
    }


def flatten_report(report: dict) -> list[dict]:
    """Flatten the nested report to one dict per check, keyed to DQ_REPORT_ROW_SCHEMA."""
    return [
        {
            "run_timestamp": report["run_timestamp"],
            "check_type": check["check_type"],
            "table": check.get("table"),
            "column": check.get("column"),
            "measurement": check.get("measurement"),
            "concept_id": check.get("concept_id"),
            "range": check.get("range"),
            "relationship": check.get("relationship"),
            "total_rows": check.get("total_rows"),
            "violations": check.get("violations"),
            "orphan_count": check.get("orphan_count"),
            "passed": check["passed"],
        }
        for check in report["checks"]
    ]


def main():
    # awsglue is only available inside the Glue runtime; import here so the
    # module stays importable by local tests.
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions
    from pyspark.context import SparkContext

    args = getResolvedOptions(sys.argv, ["JOB_NAME", "target_path", "dq_output_path"])

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    target_path = args["target_path"]
    dq_output_path = args["dq_output_path"]

    print(f"Reading OMOP tables from {target_path}")
    person_df = spark.read.parquet(f"{target_path}/person/")
    visit_df = spark.read.parquet(f"{target_path}/visit_occurrence/")
    measurement_df = spark.read.parquet(f"{target_path}/measurement/")

    report = run_all_checks(person_df, visit_df, measurement_df)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    report_df = spark.createDataFrame(flatten_report(report), DQ_REPORT_ROW_SCHEMA)
    report_df.coalesce(1).write.mode("append").json(f"{dq_output_path}/data_quality_report/")
    print(f"Wrote {report['total_checks']} check rows to {dq_output_path}/data_quality_report/")

    job.commit()


if __name__ == "__main__":
    main()
