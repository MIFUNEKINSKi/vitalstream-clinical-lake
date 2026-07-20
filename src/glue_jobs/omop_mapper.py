"""PySpark functions to map FHIR-extracted DataFrames to OMOP CDM v5.4 tables.

Each function takes parsed FHIR DataFrames and returns a DataFrame conforming
to the OMOP schema defined in src.shared.omop_schema. Uses native Spark operations:
broadcast joins for vocabulary lookups, monotonically_increasing_id for surrogate keys.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    lit,
    monotonically_increasing_id,
    regexp_replace,
    split,
    to_date,
    to_timestamp,
)
from pyspark.sql.types import FloatType, IntegerType, LongType

from src.data_generator.vocabulary import (
    GENDER_CONCEPT_MAP,
    LOINC_TO_OMOP,
    VISIT_CONCEPT_MAP,
)
from src.shared.constants import MEASUREMENT_TYPE_CONCEPT_ID, VISIT_TYPE_CONCEPT_ID


def _build_lookup_df(spark: SparkSession, mapping: dict, key_col: str, val_col: str) -> DataFrame:
    """Create a small broadcast-joinable DataFrame from a dict mapping."""
    rows = [(k, v) for k, v in mapping.items()]
    return spark.createDataFrame(rows, [key_col, val_col])


def map_to_person(spark: SparkSession, patients_df: DataFrame) -> DataFrame:
    """Map FHIR Patient resources to OMOP person table.

    Input columns: patient_fhir_id, gender, birth_date, mrn
    Output: OMOP person schema
    """
    gender_lookup = _build_lookup_df(spark, GENDER_CONCEPT_MAP, "gender", "gender_concept_id")

    return (
        patients_df
        .withColumn("person_id", monotonically_increasing_id())
        .join(broadcast(gender_lookup), on="gender", how="left")
        .select(
            col("person_id").cast(LongType()),
            coalesce(col("gender_concept_id"), lit(0)).cast(IntegerType()).alias("gender_concept_id"),
            split(col("birth_date"), "-")[0].cast(IntegerType()).alias("year_of_birth"),
            split(col("birth_date"), "-")[1].cast(IntegerType()).alias("month_of_birth"),
            split(col("birth_date"), "-")[2].cast(IntegerType()).alias("day_of_birth"),
            to_timestamp(col("birth_date")).alias("birth_datetime"),
            lit(0).cast(IntegerType()).alias("race_concept_id"),
            lit(0).cast(IntegerType()).alias("ethnicity_concept_id"),
            col("mrn").alias("person_source_value"),
            col("gender").alias("gender_source_value"),
            col("patient_fhir_id"),
        )
    )


def map_to_visit_occurrence(
    spark: SparkSession,
    encounters_df: DataFrame,
    person_df: DataFrame,
) -> DataFrame:
    """Map FHIR Encounter resources to OMOP visit_occurrence table.

    Input columns:
        encounters_df: encounter_fhir_id, class_code, period_start, period_end, patient_ref
        person_df: person_id, patient_fhir_id (from map_to_person output)
    """
    visit_lookup = _build_lookup_df(spark, VISIT_CONCEPT_MAP, "class_code", "visit_concept_id")

    # Extract patient FHIR ID from reference ("Patient/abc" → "abc")
    encounters_with_pid = (
        encounters_df
        .withColumn("patient_fhir_id", regexp_replace(col("patient_ref"), "^Patient/", ""))
    )

    person_lookup = person_df.select("person_id", "patient_fhir_id")

    return (
        encounters_with_pid
        .join(broadcast(person_lookup), on="patient_fhir_id", how="inner")
        .join(broadcast(visit_lookup), on="class_code", how="left")
        .withColumn("visit_occurrence_id", monotonically_increasing_id())
        .select(
            col("visit_occurrence_id").cast(LongType()),
            col("person_id").cast(LongType()),
            coalesce(col("visit_concept_id"), lit(0)).cast(IntegerType()).alias("visit_concept_id"),
            to_date(col("period_start")).alias("visit_start_date"),
            to_timestamp(col("period_start")).alias("visit_start_datetime"),
            to_date(col("period_end")).alias("visit_end_date"),
            to_timestamp(col("period_end")).alias("visit_end_datetime"),
            lit(VISIT_TYPE_CONCEPT_ID).cast(IntegerType()).alias("visit_type_concept_id"),
            col("class_code").alias("visit_source_value"),
            col("encounter_fhir_id"),
        )
    )


def map_to_measurement(
    spark: SparkSession,
    observations_df: DataFrame,
    person_df: DataFrame,
    visit_df: DataFrame,
) -> DataFrame:
    """Map FHIR Observation resources to OMOP measurement table.

    Uses broadcast joins for LOINC→concept_id vocabulary lookup
    and for resolving person_id / visit_occurrence_id from FHIR references.
    """
    loinc_lookup = _build_lookup_df(spark, LOINC_TO_OMOP, "loinc_code", "measurement_concept_id")

    obs_with_refs = (
        observations_df
        .withColumn("patient_fhir_id", regexp_replace(col("patient_ref"), "^Patient/", ""))
        .withColumn("encounter_fhir_id", regexp_replace(col("encounter_ref"), "^Encounter/", ""))
    )

    person_lookup = person_df.select("person_id", "patient_fhir_id")
    visit_lookup = visit_df.select(
        col("visit_occurrence_id"),
        col("encounter_fhir_id").alias("visit_encounter_fhir_id"),
    )

    return (
        obs_with_refs
        .join(broadcast(person_lookup), on="patient_fhir_id", how="inner")
        .join(
            broadcast(visit_lookup),
            obs_with_refs["encounter_fhir_id"] == visit_lookup["visit_encounter_fhir_id"],
            how="left",
        )
        .join(broadcast(loinc_lookup), on="loinc_code", how="left")
        .withColumn("measurement_id", monotonically_increasing_id())
        .select(
            col("measurement_id").cast(LongType()),
            col("person_id").cast(LongType()),
            coalesce(col("measurement_concept_id"), lit(0)).cast(IntegerType()).alias("measurement_concept_id"),
            to_date(col("effective_datetime")).alias("measurement_date"),
            to_timestamp(col("effective_datetime")).alias("measurement_datetime"),
            lit(MEASUREMENT_TYPE_CONCEPT_ID).cast(IntegerType()).alias("measurement_type_concept_id"),
            col("value").cast(FloatType()).alias("value_as_number"),
            lit(None).cast(IntegerType()).alias("unit_concept_id"),
            col("unit").alias("unit_source_value"),
            col("loinc_code").alias("measurement_source_value"),
            col("visit_occurrence_id").cast(LongType()),
        )
    )
