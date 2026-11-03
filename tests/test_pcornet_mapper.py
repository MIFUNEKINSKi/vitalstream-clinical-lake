"""Tests for PCORnet CDM mapper — verifies value-set coding, RAW_ fields and table routing."""

import re
from datetime import date

from pyspark.sql.types import StringType, StructField, StructType

from src.glue_jobs.fhir_parser import (
    extract_encounters,
    extract_observations,
    extract_patients,
)
from src.glue_jobs.pcornet_mapper import (
    map_to_demographic,
    map_to_encounter,
    map_to_obs_clin,
    map_to_vital,
)
from src.shared.pcornet_schema import (
    DEMOGRAPHIC_SCHEMA,
    ENCOUNTER_SCHEMA,
    OBS_CLIN_SCHEMA,
    VITAL_SCHEMA,
)

PATIENT_COLUMNS = StructType([
    StructField("patient_fhir_id", StringType()),
    StructField("gender", StringType()),
    StructField("birth_date", StringType()),
])


def _build_pcornet_tables(spark, sample_bundle_df):
    demographic = map_to_demographic(spark, extract_patients(sample_bundle_df))
    encounter = map_to_encounter(spark, extract_encounters(sample_bundle_df), demographic)
    observations = extract_observations(sample_bundle_df)
    vital = map_to_vital(spark, observations, demographic, encounter)
    obs_clin = map_to_obs_clin(spark, observations, demographic, encounter)
    return demographic, encounter, vital, obs_clin


def _types(schema):
    return [(f.name, f.dataType) for f in schema.fields]


def test_outputs_match_pcornet_schemas(spark, sample_bundle_df):
    demographic, encounter, vital, obs_clin = _build_pcornet_tables(spark, sample_bundle_df)

    assert _types(demographic.schema) == _types(DEMOGRAPHIC_SCHEMA)
    assert _types(encounter.schema) == _types(ENCOUNTER_SCHEMA)
    assert _types(vital.schema) == _types(VITAL_SCHEMA)
    assert _types(obs_clin.schema) == _types(OBS_CLIN_SCHEMA)


def test_map_to_demographic_sex_and_raw_sex(spark, sample_bundle_df):
    demographic = map_to_demographic(spark, extract_patients(sample_bundle_df))

    row = demographic.first()
    assert row.PATID == "patient-001"
    assert row.SEX == "M"
    assert row.RAW_SEX == "male"
    assert row.BIRTH_DATE == date(1985, 3, 15)


def test_map_to_demographic_race_ethnicity_no_information(spark, sample_bundle_df):
    demographic = map_to_demographic(spark, extract_patients(sample_bundle_df))

    row = demographic.first()
    assert row.HISPANIC == "NI"
    assert row.RACE == "NI"
    assert row.RAW_HISPANIC is None
    assert row.RAW_RACE is None


def test_map_to_demographic_unknown_and_missing_gender(spark):
    patients = spark.createDataFrame(
        [("p-unknown", "unknown", "1990-01-01"), ("p-missing", None, "1990-01-01"), ("p-odd", "x", "1990-01-01")],
        PATIENT_COLUMNS,
    )
    rows = {r.PATID: r for r in map_to_demographic(spark, patients).collect()}

    assert rows["p-unknown"].SEX == "UN"
    assert rows["p-missing"].SEX == "NI"
    assert rows["p-odd"].SEX == "OT"
    assert rows["p-odd"].RAW_SEX == "x"


def test_map_to_encounter_enc_type(spark, sample_bundle_df):
    demographic, encounter, _, _ = _build_pcornet_tables(spark, sample_bundle_df)

    row = encounter.first()
    assert row.ENC_TYPE == "AV"
    assert row.RAW_ENC_TYPE == "AMB"
    assert row.PATID == "patient-001"
    assert re.fullmatch(r"\d{2}:\d{2}", row.ADMIT_TIME)


def test_map_to_encounter_emergency_and_orphans(spark):
    demographic = map_to_demographic(
        spark, spark.createDataFrame([("p1", "female", "1970-05-05")], PATIENT_COLUMNS)
    )
    encounters = spark.createDataFrame(
        [
            ("e1", "finished", "EMER", "2025-01-01T08:00:00", "2025-01-01T12:30:00", "Patient/p1"),
            ("e2", "finished", "AMB", "2025-01-02T08:00:00", None, "Patient/not-in-demographic"),
        ],
        "encounter_fhir_id string, status string, class_code string, "
        "period_start string, period_end string, patient_ref string",
    )
    rows = map_to_encounter(spark, encounters, demographic).collect()

    assert len(rows) == 1  # orphan encounter dropped, same as OMOP visit_occurrence
    assert rows[0].ENC_TYPE == "ED"
    assert rows[0].ADMIT_TIME == "08:00"
    assert rows[0].DISCHARGE_TIME == "12:30"


def test_blood_pressure_collapses_to_one_vital_row(spark, sample_bundle_df):
    _, encounter, vital, _ = _build_pcornet_tables(spark, sample_bundle_df)

    rows = vital.collect()
    assert len(rows) == 1
    row = rows[0]
    assert row.SYSTOLIC is not None and row.DIASTOLIC is not None
    assert row.RAW_SYSTOLIC is not None and row.RAW_DIASTOLIC is not None
    assert row.VITAL_SOURCE == "HC"
    assert row.ENCOUNTERID == encounter.first().ENCOUNTERID
    assert row.MEASURE_DATE == date(2025, 6, 15)
    assert row.MEASURE_TIME == "09:15"
    assert row.HT is None and row.WT is None and row.ORIGINAL_BMI is None


def test_heart_rate_goes_to_obs_clin_with_source_code(spark, sample_bundle_df):
    _, _, _, obs_clin = _build_pcornet_tables(spark, sample_bundle_df)

    rows = obs_clin.collect()
    assert len(rows) == 1
    row = rows[0]
    assert row.OBSCLIN_CODE == "8867-4"  # source LOINC kept, no concept_id mapping
    assert row.OBSCLIN_TYPE == "LC"
    assert row.OBSCLIN_RESULT_UNIT == "/min"
    assert row.OBSCLIN_RESULT_MODIFIER == "EQ"
    assert row.RAW_OBSCLIN_CODE == "8867-4"
    assert row.RAW_OBSCLIN_UNIT == "/min"
    assert row.OBSCLIN_RESULT_NUM is not None


def test_blood_pressure_codes_not_in_obs_clin(spark, sample_bundle_df):
    _, _, _, obs_clin = _build_pcornet_tables(spark, sample_bundle_df)

    codes = {r.OBSCLIN_CODE for r in obs_clin.collect()}
    assert "8480-6" not in codes
    assert "8462-4" not in codes
