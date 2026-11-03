"""Data quality checks for PCORnet CDM tables, in the spirit of PCORnet data curation.

Runs required-field, value-set conformance, primary-key uniqueness and
referential integrity checks over DEMOGRAPHIC / ENCOUNTER / VITAL / OBS_CLIN,
plus a row-count reconciliation against the OMOP tables built from the same
FHIR parse. Produces the same report shape as data_quality.run_all_checks.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, countDistinct, lit, when
from pyspark.sql.functions import sum as spark_sum

from src.data_generator.vocabulary import (
    PCORNET_ENC_TYPE_VALUES,
    PCORNET_OBSCLIN_TYPE_VALUES,
    PCORNET_SEX_VALUES,
)


def run_required_field_checks(
    demographic_df: DataFrame,
    encounter_df: DataFrame,
    vital_df: DataFrame,
    obs_clin_df: DataFrame,
) -> list[dict]:
    """Required fields must be populated — one aggregation pass per table."""
    checks = []

    required_specs = [
        ("DEMOGRAPHIC", demographic_df, ["PATID", "BIRTH_DATE", "SEX"]),
        ("ENCOUNTER", encounter_df, ["ENCOUNTERID", "PATID", "ADMIT_DATE", "ENC_TYPE"]),
        ("VITAL", vital_df, ["VITALID", "PATID", "MEASURE_DATE", "VITAL_SOURCE"]),
        ("OBS_CLIN", obs_clin_df, ["OBSCLINID", "PATID", "OBSCLIN_START_DATE", "OBSCLIN_TYPE", "OBSCLIN_CODE"]),
    ]

    for table_name, df, columns in required_specs:
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
                "check_type": "required_field",
                "table": table_name,
                "column": col_name,
                "total_rows": total,
                "violations": null_count,
                "passed": null_count == 0,
            })

    return checks


def run_value_set_checks(
    demographic_df: DataFrame,
    encounter_df: DataFrame,
    obs_clin_df: DataFrame,
) -> list[dict]:
    """Coded fields must hold a permissible PCORnet value (null counts as a violation)."""
    checks = []

    value_set_specs = [
        ("DEMOGRAPHIC", demographic_df, "SEX", PCORNET_SEX_VALUES),
        ("ENCOUNTER", encounter_df, "ENC_TYPE", PCORNET_ENC_TYPE_VALUES),
        ("OBS_CLIN", obs_clin_df, "OBSCLIN_TYPE", PCORNET_OBSCLIN_TYPE_VALUES),
    ]

    for table_name, df, col_name, allowed in value_set_specs:
        conforms = col(col_name).isin(sorted(allowed))
        agg_row = df.agg(
            count(lit(1)).alias("total_rows"),
            spark_sum(when(conforms, 0).otherwise(1)).alias("violations"),
        ).first()
        violations = agg_row["violations"] or 0
        checks.append({
            "check_type": "value_set",
            "table": table_name,
            "column": col_name,
            "value_set": ",".join(sorted(allowed)),
            "total_rows": agg_row["total_rows"],
            "violations": violations,
            "passed": violations == 0,
        })

    return checks


def run_primary_key_checks(
    demographic_df: DataFrame,
    encounter_df: DataFrame,
    vital_df: DataFrame,
    obs_clin_df: DataFrame,
) -> list[dict]:
    """Primary keys must be unique: violations = rows minus distinct keys."""
    checks = []

    pk_specs = [
        ("DEMOGRAPHIC", demographic_df, "PATID"),
        ("ENCOUNTER", encounter_df, "ENCOUNTERID"),
        ("VITAL", vital_df, "VITALID"),
        ("OBS_CLIN", obs_clin_df, "OBSCLINID"),
    ]

    for table_name, df, key_col in pk_specs:
        agg_row = df.agg(
            count(lit(1)).alias("total_rows"),
            countDistinct(col(key_col)).alias("distinct_keys"),
        ).first()
        duplicates = agg_row["total_rows"] - agg_row["distinct_keys"]
        checks.append({
            "check_type": "primary_key",
            "table": table_name,
            "column": key_col,
            "total_rows": agg_row["total_rows"],
            "violations": duplicates,
            "passed": duplicates == 0,
        })

    return checks


def run_pcornet_referential_integrity_checks(
    demographic_df: DataFrame,
    encounter_df: DataFrame,
    vital_df: DataFrame,
    obs_clin_df: DataFrame,
) -> list[dict]:
    """Every PATID / ENCOUNTERID must resolve to its parent table, via anti-joins."""
    checks = []
    patids = demographic_df.select("PATID")
    encounter_ids = encounter_df.select("ENCOUNTERID")

    ri_specs = [
        ("ENCOUNTER.PATID → DEMOGRAPHIC.PATID", encounter_df.select("PATID"), patids, "PATID"),
        ("VITAL.PATID → DEMOGRAPHIC.PATID", vital_df.select("PATID"), patids, "PATID"),
        ("OBS_CLIN.PATID → DEMOGRAPHIC.PATID", obs_clin_df.select("PATID"), patids, "PATID"),
        (
            "VITAL.ENCOUNTERID → ENCOUNTER.ENCOUNTERID",
            vital_df.filter(col("ENCOUNTERID").isNotNull()).select("ENCOUNTERID"),
            encounter_ids,
            "ENCOUNTERID",
        ),
        (
            "OBS_CLIN.ENCOUNTERID → ENCOUNTER.ENCOUNTERID",
            obs_clin_df.filter(col("ENCOUNTERID").isNotNull()).select("ENCOUNTERID"),
            encounter_ids,
            "ENCOUNTERID",
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


def run_reconciliation_checks(
    person_df: DataFrame,
    visit_df: DataFrame,
    measurement_df: DataFrame,
    demographic_df: DataFrame,
    encounter_df: DataFrame,
    vital_df: DataFrame,
    obs_clin_df: DataFrame,
) -> list[dict]:
    """Cross-model reconciliation: both CDMs come from one parse, so counts must agree.

    Every OMOP measurement row lands in PCORnet either as an OBS_CLIN row or as
    one populated SYSTOLIC / DIASTOLIC value on a VITAL row.
    """
    vital_values = vital_df.agg(
        (count(col("SYSTOLIC")) + count(col("DIASTOLIC"))).alias("n")
    ).first()["n"]

    pairs = [
        ("person ↔ DEMOGRAPHIC", person_df.count(), demographic_df.count()),
        ("visit_occurrence ↔ ENCOUNTER", visit_df.count(), encounter_df.count()),
        ("measurement ↔ OBS_CLIN + VITAL(SYSTOLIC, DIASTOLIC)", measurement_df.count(),
         obs_clin_df.count() + vital_values),
    ]

    return [
        {
            "check_type": "omop_pcornet_reconciliation",
            "relationship": relationship,
            "omop_rows": omop_rows,
            "pcornet_rows": pcornet_rows,
            "violations": abs(omop_rows - pcornet_rows),
            "passed": omop_rows == pcornet_rows,
        }
        for relationship, omop_rows, pcornet_rows in pairs
    ]


def run_all_pcornet_checks(
    demographic_df: DataFrame,
    encounter_df: DataFrame,
    vital_df: DataFrame,
    obs_clin_df: DataFrame,
    omop: tuple[DataFrame, DataFrame, DataFrame] | None = None,
) -> dict:
    """Run all PCORnet DQ checks and return a structured report.

    omop is an optional (person, visit_occurrence, measurement) tuple; when
    given, the OMOP ↔ PCORnet reconciliation checks run too.
    """
    tables = (demographic_df, encounter_df, vital_df, obs_clin_df) + (omop or ())
    for df in tables:
        df.cache()

    try:
        all_checks = (
            run_required_field_checks(demographic_df, encounter_df, vital_df, obs_clin_df)
            + run_value_set_checks(demographic_df, encounter_df, obs_clin_df)
            + run_primary_key_checks(demographic_df, encounter_df, vital_df, obs_clin_df)
            + run_pcornet_referential_integrity_checks(demographic_df, encounter_df, vital_df, obs_clin_df)
        )
        if omop is not None:
            all_checks += run_reconciliation_checks(*omop, demographic_df, encounter_df, vital_df, obs_clin_df)
    finally:
        for df in tables:
            df.unpersist()

    all_passed = all(c["passed"] for c in all_checks)

    return {
        "run_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "overall_result": "PASS" if all_passed else "FAIL",
        "total_checks": len(all_checks),
        "passed_checks": sum(1 for c in all_checks if c["passed"]),
        "failed_checks": sum(1 for c in all_checks if not c["passed"]),
        "checks": all_checks,
    }
