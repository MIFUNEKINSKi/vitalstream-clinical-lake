"""Tests for data quality checks on PCORnet tables and OMOP ↔ PCORnet reconciliation."""

from datetime import date

from pyspark.sql.types import StructField, StructType

from src.glue_jobs.fhir_parser import (
    extract_encounters,
    extract_observations,
    extract_patients,
)
from src.glue_jobs.omop_mapper import (
    map_to_measurement,
    map_to_person,
    map_to_visit_occurrence,
)
from src.glue_jobs.pcornet_data_quality import (
    run_all_pcornet_checks,
    run_pcornet_referential_integrity_checks,
    run_primary_key_checks,
    run_reconciliation_checks,
    run_required_field_checks,
    run_value_set_checks,
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
)


def _build_both_models(spark, sample_bundle_df):
    """Helper to build OMOP and PCORnet tables from one parse of the sample fixture."""
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    observations = extract_observations(sample_bundle_df)

    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)
    measurements = map_to_measurement(spark, observations, person, visits)

    demographic = map_to_demographic(spark, patients)
    encounter = map_to_encounter(spark, encounters, demographic)
    vital = map_to_vital(spark, observations, demographic, encounter)
    obs_clin = map_to_obs_clin(spark, observations, demographic, encounter)

    return (person, visits, measurements), (demographic, encounter, vital, obs_clin)


def _nullable(schema):
    return StructType([StructField(f.name, f.dataType, nullable=True) for f in schema.fields])


def _demographic_row(patid, sex):
    return (patid, date(1980, 1, 1), None, sex, "NI", "NI", None, None, None)


def _encounter_row(encounter_id, patid, enc_type):
    return (encounter_id, patid, date(2025, 1, 1), "08:00", None, None, enc_type, None)


def _obs_clin_row(obsclin_id, patid):
    return (obsclin_id, patid, None, date(2025, 1, 1), "08:00", "LC", "8867-4", 72.0, "EQ", "/min", "HC",
            "Heart rate", "8867-4", "LC", "72", "/min")


def test_required_field_checks_pass_on_valid_data(spark, sample_bundle_df):
    _, pcornet = _build_both_models(spark, sample_bundle_df)

    for check in run_required_field_checks(*pcornet):
        assert check["passed"], f"Required field missing: {check['table']}.{check['column']}"


def test_value_set_checks_pass_on_valid_data(spark, sample_bundle_df):
    _, (demographic, encounter, _, obs_clin) = _build_both_models(spark, sample_bundle_df)

    for check in run_value_set_checks(demographic, encounter, obs_clin):
        assert check["passed"], f"Value set check failed: {check['table']}.{check['column']}"


def test_primary_key_and_referential_integrity_pass(spark, sample_bundle_df):
    _, pcornet = _build_both_models(spark, sample_bundle_df)

    for check in run_primary_key_checks(*pcornet):
        assert check["passed"], f"Duplicate keys: {check['table']}.{check['column']}"
    for check in run_pcornet_referential_integrity_checks(*pcornet):
        assert check["passed"], f"RI check failed: {check['relationship']}"


def test_run_all_pcornet_checks_with_reconciliation(spark, sample_bundle_df):
    omop, pcornet = _build_both_models(spark, sample_bundle_df)
    report = run_all_pcornet_checks(*pcornet, omop=omop)

    assert report["overall_result"] == "PASS"
    assert report["failed_checks"] == 0
    recon = [c for c in report["checks"] if c["check_type"] == "omop_pcornet_reconciliation"]
    assert len(recon) == 3
    measurement_recon = next(c for c in recon if c["relationship"].startswith("measurement"))
    assert measurement_recon["omop_rows"] == 3  # 1 OBS_CLIN heart rate + VITAL systolic + diastolic


def test_value_set_detects_invalid_sex(spark, sample_bundle_df):
    _, (_, encounter, _, obs_clin) = _build_both_models(spark, sample_bundle_df)
    bad_demographic = spark.createDataFrame(
        [_demographic_row("p1", "M"), _demographic_row("p2", "X"), _demographic_row("p3", None)],
        _nullable(DEMOGRAPHIC_SCHEMA),  # allow the null SEX the check must catch
    )
    checks = run_value_set_checks(bad_demographic, encounter, obs_clin)

    sex_check = next(c for c in checks if c["column"] == "SEX")
    assert not sex_check["passed"]
    assert sex_check["violations"] == 2  # "X" and null


def test_value_set_detects_invalid_enc_type(spark, sample_bundle_df):
    _, (demographic, _, _, obs_clin) = _build_both_models(spark, sample_bundle_df)
    bad_encounter = spark.createDataFrame([_encounter_row("e1", "patient-001", "ZZ")], ENCOUNTER_SCHEMA)
    checks = run_value_set_checks(demographic, bad_encounter, obs_clin)

    enc_check = next(c for c in checks if c["column"] == "ENC_TYPE")
    assert not enc_check["passed"]
    assert enc_check["violations"] == 1


def test_referential_integrity_detects_orphan_obs_clin(spark, sample_bundle_df):
    _, (demographic, encounter, vital, _) = _build_both_models(spark, sample_bundle_df)
    orphan_obs = spark.createDataFrame([_obs_clin_row("o1", "no-such-patient")], OBS_CLIN_SCHEMA)
    checks = run_pcornet_referential_integrity_checks(demographic, encounter, vital, orphan_obs)

    obs_check = next(c for c in checks if c["relationship"] == "OBS_CLIN.PATID → DEMOGRAPHIC.PATID")
    assert not obs_check["passed"]
    assert obs_check["orphan_count"] == 1


def test_primary_key_detects_duplicate_encounterid(spark, sample_bundle_df):
    _, (demographic, _, vital, obs_clin) = _build_both_models(spark, sample_bundle_df)
    dup_encounter = spark.createDataFrame(
        [_encounter_row("e1", "patient-001", "AV"), _encounter_row("e1", "patient-001", "AV")],
        ENCOUNTER_SCHEMA,
    )
    checks = run_primary_key_checks(demographic, dup_encounter, vital, obs_clin)

    enc_check = next(c for c in checks if c["table"] == "ENCOUNTER")
    assert not enc_check["passed"]
    assert enc_check["violations"] == 1


def test_reconciliation_detects_missing_encounter(spark, sample_bundle_df):
    omop, (demographic, encounter, vital, obs_clin) = _build_both_models(spark, sample_bundle_df)
    checks = run_reconciliation_checks(*omop, demographic, encounter.limit(0), vital, obs_clin)

    visit_check = next(c for c in checks if c["relationship"].startswith("visit_occurrence"))
    assert not visit_check["passed"]
    assert visit_check["omop_rows"] == 1
    assert visit_check["pcornet_rows"] == 0
