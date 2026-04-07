"""Tests for data quality checks on OMOP tables."""

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
    data = [
        (1, 1, 3027018, "2025-01-01", None, 32817, 999.0, None, None, "8867-4", None),
    ]
    columns = [
        "measurement_id", "person_id", "measurement_concept_id",
        "measurement_date", "measurement_datetime", "measurement_type_concept_id",
        "value_as_number", "unit_concept_id", "unit_source_value",
        "measurement_source_value", "visit_occurrence_id",
    ]
    bad_df = spark.createDataFrame(data, columns)
    checks = run_range_checks(bad_df)

    hr_check = next(c for c in checks if c["concept_id"] == 3027018)
    assert not hr_check["passed"]
    assert hr_check["violations"] == 1
