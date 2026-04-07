"""Data quality checks for OMOP CDM tables.

Runs null checks, range validation, and referential integrity checks.
Produces a structured JSON report with pass/fail per check.
"""

from __future__ import annotations

import json
from datetime import datetime

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, count, when


def run_null_checks(person_df: DataFrame, measurement_df: DataFrame, visit_df: DataFrame) -> list[dict]:
    """Check critical columns for unexpected nulls."""
    checks = []

    null_specs = [
        ("person", person_df, ["person_id", "gender_concept_id", "year_of_birth"]),
        ("measurement", measurement_df, ["measurement_id", "person_id", "measurement_date", "value_as_number"]),
        ("visit_occurrence", visit_df, ["visit_occurrence_id", "person_id", "visit_start_date"]),
    ]

    for table_name, df, columns in null_specs:
        total = df.count()
        for col_name in columns:
            null_count = df.filter(col(col_name).isNull()).count()
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
    """Validate vital sign measurements fall within clinically plausible ranges."""
    checks = []

    range_specs = [
        (3027018, "Heart Rate", 20, 300),
        (3004249, "Systolic BP", 50, 300),
        (3012888, "Diastolic BP", 20, 200),
        (3020891, "Body Temperature", 30, 45),
        (3024171, "Respiratory Rate", 4, 60),
        (3016502, "Oxygen Saturation", 50, 100),
    ]

    for concept_id, name, low, high in range_specs:
        subset = measurement_df.filter(col("measurement_concept_id") == concept_id)
        total = subset.count()
        if total == 0:
            continue

        violations = subset.filter(
            (col("value_as_number") < low) | (col("value_as_number") > high)
        ).count()

        checks.append({
            "check_type": "range_check",
            "measurement": name,
            "concept_id": concept_id,
            "range": f"[{low}, {high}]",
            "total_rows": total,
            "violations": violations,
            "passed": violations == 0,
        })

    return checks


def run_referential_integrity_checks(
    person_df: DataFrame,
    visit_df: DataFrame,
    measurement_df: DataFrame,
) -> list[dict]:
    """Verify foreign key relationships between OMOP tables."""
    checks = []

    # measurement.person_id → person.person_id
    person_ids = person_df.select("person_id")
    orphan_measurement_persons = (
        measurement_df.select("person_id")
        .subtract(person_ids)
        .count()
    )
    checks.append({
        "check_type": "referential_integrity",
        "relationship": "measurement.person_id → person.person_id",
        "orphan_count": orphan_measurement_persons,
        "passed": orphan_measurement_persons == 0,
    })

    # visit_occurrence.person_id → person.person_id
    orphan_visit_persons = (
        visit_df.select("person_id")
        .subtract(person_ids)
        .count()
    )
    checks.append({
        "check_type": "referential_integrity",
        "relationship": "visit_occurrence.person_id → person.person_id",
        "orphan_count": orphan_visit_persons,
        "passed": orphan_visit_persons == 0,
    })

    # measurement.visit_occurrence_id → visit_occurrence.visit_occurrence_id
    visit_ids = visit_df.select("visit_occurrence_id")
    measurement_visit_ids = measurement_df.filter(
        col("visit_occurrence_id").isNotNull()
    ).select("visit_occurrence_id")
    orphan_measurement_visits = measurement_visit_ids.subtract(visit_ids).count()
    checks.append({
        "check_type": "referential_integrity",
        "relationship": "measurement.visit_occurrence_id → visit_occurrence.visit_occurrence_id",
        "orphan_count": orphan_measurement_visits,
        "passed": orphan_measurement_visits == 0,
    })

    return checks


def run_all_checks(
    person_df: DataFrame,
    visit_df: DataFrame,
    measurement_df: DataFrame,
) -> dict:
    """Run all DQ checks and return a structured report."""
    null_checks = run_null_checks(person_df, measurement_df, visit_df)
    range_checks = run_range_checks(measurement_df)
    ri_checks = run_referential_integrity_checks(person_df, visit_df, measurement_df)

    all_checks = null_checks + range_checks + ri_checks
    all_passed = all(c["passed"] for c in all_checks)

    return {
        "run_timestamp": datetime.utcnow().isoformat(),
        "overall_result": "PASS" if all_passed else "FAIL",
        "total_checks": len(all_checks),
        "passed_checks": sum(1 for c in all_checks if c["passed"]),
        "failed_checks": sum(1 for c in all_checks if not c["passed"]),
        "checks": all_checks,
    }
