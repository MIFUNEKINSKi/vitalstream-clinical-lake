"""Tests for data quality checks on OMOP tables."""

from datetime import date

from src.data_generator.vocabulary import LOINC_TO_OMOP
from src.glue_jobs.data_quality import (
    run_all_checks,
    run_null_checks,
    run_range_checks,
    run_referential_integrity_checks,
)
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
from src.shared.constants import MEASUREMENT_TYPE_CONCEPT_ID
from src.shared.omop_schema import MEASUREMENT_SCHEMA


def _build_omop_tables(spark, sample_bundle_df):
    """Helper to build all OMOP tables from sample fixture."""
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    observations = extract_observations(sample_bundle_df)

    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)
    measurements = map_to_measurement(spark, observations, person, visits)

    return person, visits, measurements


def test_null_checks_pass_on_valid_data(spark, sample_bundle_df):
    person, visits, measurements = _build_omop_tables(spark, sample_bundle_df)
    checks = run_null_checks(person, measurements, visits)

    for check in checks:
        assert check["passed"], f"Null check failed: {check['table']}.{check['column']}"


def test_range_checks_pass_on_valid_data(spark, sample_bundle_df):
    person, visits, measurements = _build_omop_tables(spark, sample_bundle_df)
    checks = run_range_checks(measurements)

    for check in checks:
        assert check["passed"], f"Range check failed: {check['measurement']}"


def test_referential_integrity_passes(spark, sample_bundle_df):
    person, visits, measurements = _build_omop_tables(spark, sample_bundle_df)
    checks = run_referential_integrity_checks(person, visits, measurements)

    for check in checks:
        assert check["passed"], f"RI check failed: {check['relationship']}"


def test_run_all_checks_overall_pass(spark, sample_bundle_df):
    person, visits, measurements = _build_omop_tables(spark, sample_bundle_df)
    report = run_all_checks(person, visits, measurements)

    assert report["overall_result"] == "PASS"
    assert report["failed_checks"] == 0
    assert report["total_checks"] > 0


def test_range_check_detects_out_of_range(spark):
    """Inject an out-of-range heart rate and verify DQ catches it."""
    heart_rate_concept_id = LOINC_TO_OMOP["8867-4"]
    data = [
        (1, 1, heart_rate_concept_id, date(2025, 1, 1), None,
         MEASUREMENT_TYPE_CONCEPT_ID, 999.0, None, None, "8867-4", None),
    ]
    bad_df = spark.createDataFrame(data, MEASUREMENT_SCHEMA)
    checks = run_range_checks(bad_df)

    hr_check = next(c for c in checks if c["concept_id"] == heart_rate_concept_id)
    assert not hr_check["passed"]
    assert hr_check["violations"] == 1
