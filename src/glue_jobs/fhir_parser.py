"""PySpark functions to flatten FHIR R4 Bundle JSON into typed DataFrames.

Uses native Spark operations (explode, select, filter) — no UDFs or toPandas().
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, explode


def read_fhir_bundles(spark: SparkSession, path: str) -> DataFrame:
    """Read FHIR Bundle JSON files from a path into a DataFrame."""
    return spark.read.option("multiline", "true").json(path)


def extract_patients(bundle_df: DataFrame) -> DataFrame:
    """Extract Patient resources from FHIR Bundles.

    Returns DataFrame with columns:
        patient_fhir_id, gender, birth_date, mrn, family_name, given_name
    """
    entries = bundle_df.select(explode("entry").alias("entry"))

    return (
        entries.filter(col("entry.resource.resourceType") == "Patient")
        .select(
            col("entry.resource.id").alias("patient_fhir_id"),
            col("entry.resource.gender").alias("gender"),
            col("entry.resource.birthDate").alias("birth_date"),
            col("entry.resource.identifier")[0]["value"].alias("mrn"),
            col("entry.resource.name")[0]["family"].alias("family_name"),
            col("entry.resource.name")[0]["given"][0].alias("given_name"),
        )
    )


def extract_encounters(bundle_df: DataFrame) -> DataFrame:
    """Extract Encounter resources from FHIR Bundles.

    Returns DataFrame with columns:
        encounter_fhir_id, status, class_code, period_start, period_end,
        patient_ref
    """
    entries = bundle_df.select(explode("entry").alias("entry"))

    return (
        entries.filter(col("entry.resource.resourceType") == "Encounter")
        .select(
            col("entry.resource.id").alias("encounter_fhir_id"),
            col("entry.resource.status").alias("status"),
            col("entry.resource.class.code").alias("class_code"),
            col("entry.resource.period.start").alias("period_start"),
            col("entry.resource.period.end").alias("period_end"),
            col("entry.resource.subject.reference").alias("patient_ref"),
        )
    )


def extract_observations(bundle_df: DataFrame) -> DataFrame:
    """Extract Observation resources from FHIR Bundles.

    Returns DataFrame with columns:
        observation_fhir_id, loinc_code, loinc_display, patient_ref,
        encounter_ref, effective_datetime, value, unit
    """
    entries = bundle_df.select(explode("entry").alias("entry"))

    return (
        entries.filter(col("entry.resource.resourceType") == "Observation")
        .select(
            col("entry.resource.id").alias("observation_fhir_id"),
            col("entry.resource.code.coding")[0]["code"].alias("loinc_code"),
            col("entry.resource.code.coding")[0]["display"].alias("loinc_display"),
            col("entry.resource.subject.reference").alias("patient_ref"),
            col("entry.resource.encounter.reference").alias("encounter_ref"),
            col("entry.resource.effectiveDateTime").alias("effective_datetime"),
            col("entry.resource.valueQuantity.value").alias("value"),
            col("entry.resource.valueQuantity.unit").alias("unit"),
        )
    )
