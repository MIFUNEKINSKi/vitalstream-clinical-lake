"""PySpark functions to map FHIR-extracted DataFrames to PCORnet CDM v6.1 tables.

Takes the same parsed FHIR DataFrames as omop_mapper and returns DataFrames
conforming to src.shared.pcornet_schema. Unlike OMOP, PCORnet does not map to
standard concept_ids: it keeps the source code plus a code type (OBSCLIN_CODE
8867-4 with OBSCLIN_TYPE 'LC'), uses short categorical value sets (SEX, ENC_TYPE),
and preserves every value as received in RAW_ columns. Keys are the FHIR
logical ids rather than integer surrogates.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    date_format,
    first,
    lit,
    monotonically_increasing_id,
    regexp_replace,
    to_date,
    to_timestamp,
    when,
)
from pyspark.sql.types import DoubleType, StringType

from src.data_generator.vocabulary import (
    FHIR_CLASS_TO_PCORNET_ENC_TYPE,
    FHIR_GENDER_TO_PCORNET_SEX,
    PCORNET_VITAL_LOINC,
)
from src.shared.constants import (
    OBSCLIN_SOURCE_HEALTHCARE,
    OBSCLIN_TYPE_LOINC,
    PCORNET_NO_INFORMATION,
    PCORNET_OTHER,
    RESULT_MODIFIER_EQUAL,
    VITAL_SOURCE_HEALTHCARE,
)


def _build_lookup_df(spark: SparkSession, mapping: dict, key_col: str, val_col: str) -> DataFrame:
    """Create a small broadcast-joinable DataFrame from a dict mapping."""
    rows = [(k, v) for k, v in mapping.items()]
    return spark.createDataFrame(rows, [key_col, val_col])


def _coded(source_col: str, mapped_col: str):
    """PCORnet null-flavor convention: NI when the source is missing, OT when present but unmapped."""
    return (
        when(col(source_col).isNull(), lit(PCORNET_NO_INFORMATION))
        .otherwise(coalesce(col(mapped_col), lit(PCORNET_OTHER)))
    )


def _hh_mm(datetime_col: str):
    """PCORnet stores times as 'HH:MM' strings alongside a DATE column."""
    return date_format(to_timestamp(col(datetime_col)), "HH:mm")


def _resolve_observation_keys(
    observations_df: DataFrame,
    demographic_df: DataFrame,
    encounter_df: DataFrame,
) -> DataFrame:
    """Attach PATID / ENCOUNTERID to observations from their FHIR references.

    Inner join to DEMOGRAPHIC and left join to ENCOUNTER, the same orphan
    handling as omop_mapper.map_to_measurement so both models reconcile.
    """
    obs_with_refs = (
        observations_df
        .withColumn("PATID", regexp_replace(col("patient_ref"), "^Patient/", ""))
        .withColumn("encounter_fhir_id", regexp_replace(col("encounter_ref"), "^Encounter/", ""))
    )

    patid_lookup = demographic_df.select("PATID")
    encounter_lookup = encounter_df.select(
        col("ENCOUNTERID"),
        col("ENCOUNTERID").alias("encounter_fhir_id"),
    )

    return (
        obs_with_refs
        .join(broadcast(patid_lookup), on="PATID", how="inner")
        .join(broadcast(encounter_lookup), on="encounter_fhir_id", how="left")
    )


def map_to_demographic(spark: SparkSession, patients_df: DataFrame) -> DataFrame:
    """Map FHIR Patient resources to PCORnet DEMOGRAPHIC.

    Input columns: patient_fhir_id, gender, birth_date
    HISPANIC and RACE are NI: the FHIR source carries no race/ethnicity extension.
    """
    sex_lookup = _build_lookup_df(spark, FHIR_GENDER_TO_PCORNET_SEX, "gender", "pcornet_sex")

    return (
        patients_df
        .join(broadcast(sex_lookup), on="gender", how="left")
        .select(
            col("patient_fhir_id").alias("PATID"),
            to_date(col("birth_date")).alias("BIRTH_DATE"),
            lit(None).cast(StringType()).alias("BIRTH_TIME"),
            _coded("gender", "pcornet_sex").alias("SEX"),
            lit(PCORNET_NO_INFORMATION).alias("HISPANIC"),
            lit(PCORNET_NO_INFORMATION).alias("RACE"),
            col("gender").alias("RAW_SEX"),
            lit(None).cast(StringType()).alias("RAW_HISPANIC"),
            lit(None).cast(StringType()).alias("RAW_RACE"),
        )
    )


def map_to_encounter(
    spark: SparkSession,
    encounters_df: DataFrame,
    demographic_df: DataFrame,
) -> DataFrame:
    """Map FHIR Encounter resources to PCORnet ENCOUNTER.

    Input columns:
        encounters_df: encounter_fhir_id, class_code, period_start, period_end, patient_ref
        demographic_df: PATID (from map_to_demographic output)
    """
    enc_type_lookup = _build_lookup_df(spark, FHIR_CLASS_TO_PCORNET_ENC_TYPE, "class_code", "pcornet_enc_type")

    return (
        encounters_df
        .withColumn("PATID", regexp_replace(col("patient_ref"), "^Patient/", ""))
        .join(broadcast(demographic_df.select("PATID")), on="PATID", how="inner")
        .join(broadcast(enc_type_lookup), on="class_code", how="left")
        .select(
            col("encounter_fhir_id").alias("ENCOUNTERID"),
            col("PATID"),
            to_date(col("period_start")).alias("ADMIT_DATE"),
            _hh_mm("period_start").alias("ADMIT_TIME"),
            to_date(col("period_end")).alias("DISCHARGE_DATE"),
            _hh_mm("period_end").alias("DISCHARGE_TIME"),
            _coded("class_code", "pcornet_enc_type").alias("ENC_TYPE"),
            col("class_code").alias("RAW_ENC_TYPE"),
        )
    )


def map_to_vital(
    spark: SparkSession,
    observations_df: DataFrame,
    demographic_df: DataFrame,
    encounter_df: DataFrame,
) -> DataFrame:
    """Map blood-pressure Observations to PCORnet VITAL.

    VITAL is wide: systolic and diastolic readings taken for the same patient,
    encounter and time collapse into one row (OMOP keeps them as two
    measurement rows).
    """
    vital_obs = _resolve_observation_keys(
        observations_df.filter(col("loinc_code").isin(list(PCORNET_VITAL_LOINC))),
        demographic_df,
        encounter_df,
    )

    def component(loinc_code: str, value_col):
        return first(when(col("loinc_code") == loinc_code, value_col), ignorenulls=True)

    loinc_for = {column: code for code, column in PCORNET_VITAL_LOINC.items()}

    return (
        vital_obs
        .groupBy("PATID", "ENCOUNTERID", "effective_datetime")
        .agg(
            component(loinc_for["SYSTOLIC"], col("value")).alias("systolic"),
            component(loinc_for["DIASTOLIC"], col("value")).alias("diastolic"),
        )
        .withColumn("VITALID", monotonically_increasing_id().cast(StringType()))
        .select(
            col("VITALID"),
            col("PATID"),
            col("ENCOUNTERID"),
            to_date(col("effective_datetime")).alias("MEASURE_DATE"),
            _hh_mm("effective_datetime").alias("MEASURE_TIME"),
            lit(VITAL_SOURCE_HEALTHCARE).alias("VITAL_SOURCE"),
            lit(None).cast(DoubleType()).alias("HT"),
            lit(None).cast(DoubleType()).alias("WT"),
            col("diastolic").cast(DoubleType()).alias("DIASTOLIC"),
            col("systolic").cast(DoubleType()).alias("SYSTOLIC"),
            lit(None).cast(DoubleType()).alias("ORIGINAL_BMI"),
            lit(PCORNET_NO_INFORMATION).alias("BP_POSITION"),
            col("diastolic").cast(StringType()).alias("RAW_DIASTOLIC"),
            col("systolic").cast(StringType()).alias("RAW_SYSTOLIC"),
            lit(None).cast(StringType()).alias("RAW_BP_POSITION"),
        )
    )


def map_to_obs_clin(
    spark: SparkSession,
    observations_df: DataFrame,
    demographic_df: DataFrame,
    encounter_df: DataFrame,
) -> DataFrame:
    """Map non-VITAL Observations (heart rate, temperature, ...) to PCORnet OBS_CLIN.

    The LOINC code is kept as received in OBSCLIN_CODE with OBSCLIN_TYPE 'LC';
    there is no concept_id lookup. Observations with no code land here too, so
    the required-field DQ check flags them instead of them silently vanishing.
    """
    is_vital = col("loinc_code").isin(list(PCORNET_VITAL_LOINC))
    obs = _resolve_observation_keys(
        observations_df.filter(col("loinc_code").isNull() | ~is_vital),
        demographic_df,
        encounter_df,
    )

    return obs.select(
        col("observation_fhir_id").alias("OBSCLINID"),
        col("PATID"),
        col("ENCOUNTERID"),
        to_date(col("effective_datetime")).alias("OBSCLIN_START_DATE"),
        _hh_mm("effective_datetime").alias("OBSCLIN_START_TIME"),
        lit(OBSCLIN_TYPE_LOINC).alias("OBSCLIN_TYPE"),
        col("loinc_code").alias("OBSCLIN_CODE"),
        col("value").cast(DoubleType()).alias("OBSCLIN_RESULT_NUM"),
        lit(RESULT_MODIFIER_EQUAL).alias("OBSCLIN_RESULT_MODIFIER"),
        col("unit").alias("OBSCLIN_RESULT_UNIT"),
        lit(OBSCLIN_SOURCE_HEALTHCARE).alias("OBSCLIN_SOURCE"),
        col("loinc_display").alias("RAW_OBSCLIN_NAME"),
        col("loinc_code").alias("RAW_OBSCLIN_CODE"),
        lit(OBSCLIN_TYPE_LOINC).alias("RAW_OBSCLIN_TYPE"),
        col("value").cast(StringType()).alias("RAW_OBSCLIN_RESULT"),
        col("unit").alias("RAW_OBSCLIN_UNIT"),
    )
