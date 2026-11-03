"""End-to-end integration tests: FHIR Bundle → OMOP CDM and PCORnet CDM tables."""

from src.glue_jobs.data_quality import run_all_checks
from src.glue_jobs.fhir_parser import (
    extract_encounters,
    extract_observations,
    extract_patients,
)
from src.glue_jobs.fhir_to_omop_etl import build_cdm_tables
from src.glue_jobs.omop_mapper import (
    map_to_measurement,
    map_to_person,
    map_to_visit_occurrence,
)
from src.glue_jobs.pcornet_data_quality import run_all_pcornet_checks


def test_full_pipeline_fhir_to_omop(spark, sample_bundle_df):
    """Verify complete pipeline: parse → map → validate across all OMOP tables."""
    # Parse FHIR
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    observations = extract_observations(sample_bundle_df)

    assert patients.count() == 1
    assert encounters.count() == 1
    assert observations.count() == 3

    # Map to OMOP
    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)
    measurements = map_to_measurement(spark, observations, person, visits)

    # Verify table row counts
    assert person.count() == 1
    assert visits.count() == 1
    assert measurements.count() == 3

    # Verify person fields
    p = person.first()
    assert p.gender_concept_id == 8507  # male
    assert p.year_of_birth == 1985
    assert p.person_source_value == "MRN-12345678"

    # Verify visit fields
    v = visits.first()
    assert v.visit_concept_id == 9202  # AMB
    assert v.visit_type_concept_id == 32817  # EHR

    # Verify measurements resolve to correct concept_ids
    m_rows = {r.measurement_source_value: r for r in measurements.collect()}
    assert m_rows["8867-4"].measurement_concept_id == 3027018  # Heart Rate
    assert m_rows["8480-6"].measurement_concept_id == 3004249  # Systolic BP
    assert m_rows["8462-4"].measurement_concept_id == 3012888  # Diastolic BP

    # Verify all measurements link to the same person
    person_ids = {r.person_id for r in measurements.collect()}
    assert len(person_ids) == 1
    assert person_ids.pop() == p.person_id

    # Run DQ checks
    report = run_all_checks(person, visits, measurements)
    assert report["overall_result"] == "PASS"
    assert report["failed_checks"] == 0


def test_one_etl_run_builds_omop_and_pcornet(spark, sample_bundle_df):
    """One build_cdm_tables call (what the Glue job runs) yields both models, and they reconcile."""
    tables = build_cdm_tables(spark, sample_bundle_df)
    omop, pcornet = tables["omop"], tables["pcornet"]

    assert omop["person"].count() == 1
    assert omop["visit_occurrence"].count() == 1
    assert omop["measurement"].count() == 3

    assert pcornet["demographic"].count() == 1
    assert pcornet["encounter"].count() == 1
    assert pcornet["vital"].count() == 1  # systolic + diastolic on one row
    assert pcornet["obs_clin"].count() == 1  # heart rate

    # Same patient and encounter identity in both models
    assert pcornet["demographic"].first().PATID == omop["person"].first().patient_fhir_id
    assert pcornet["encounter"].first().ENCOUNTERID == omop["visit_occurrence"].first().encounter_fhir_id

    omop_tables = (omop["person"], omop["visit_occurrence"], omop["measurement"])
    assert run_all_checks(*omop_tables)["overall_result"] == "PASS"

    report = run_all_pcornet_checks(
        pcornet["demographic"], pcornet["encounter"], pcornet["vital"], pcornet["obs_clin"], omop=omop_tables,
    )
    assert report["overall_result"] == "PASS", [c for c in report["checks"] if not c["passed"]]


def test_etl_can_skip_pcornet(spark, sample_bundle_df):
    tables = build_cdm_tables(spark, sample_bundle_df, include_pcornet=False)

    assert "pcornet" not in tables
    assert set(tables["omop"]) == {"person", "visit_occurrence", "measurement"}
