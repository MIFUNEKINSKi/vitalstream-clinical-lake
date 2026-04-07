"""End-to-end integration test: FHIR Bundle → OMOP CDM tables."""

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
from src.glue_jobs.data_quality import run_all_checks


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
