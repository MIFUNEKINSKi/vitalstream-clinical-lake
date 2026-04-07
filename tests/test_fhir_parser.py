"""Tests for PySpark FHIR Bundle parser."""

from src.glue_jobs.fhir_parser import (
    extract_encounters,
    extract_observations,
    extract_patients,
)


def test_extract_patients_returns_one_patient(sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    assert patients.count() == 1

    row = patients.first()
    assert row.patient_fhir_id == "patient-001"
    assert row.gender == "male"
    assert row.birth_date == "1985-03-15"
    assert row.mrn == "MRN-12345678"
    assert row.family_name == "Smith"
    assert row.given_name == "John"


def test_extract_encounters_returns_one_encounter(sample_bundle_df):
    encounters = extract_encounters(sample_bundle_df)
    assert encounters.count() == 1

    row = encounters.first()
    assert row.encounter_fhir_id == "encounter-001"
    assert row.status == "finished"
    assert row.class_code == "AMB"
    assert row.patient_ref == "Patient/patient-001"


def test_extract_observations_returns_three(sample_bundle_df):
    observations = extract_observations(sample_bundle_df)
    assert observations.count() == 3

    loinc_codes = {row.loinc_code for row in observations.collect()}
    assert loinc_codes == {"8867-4", "8480-6", "8462-4"}


def test_observation_has_value_and_unit(sample_bundle_df):
    observations = extract_observations(sample_bundle_df)
    hr = observations.filter(observations.loinc_code == "8867-4").first()

    assert hr.value == 72.0
    assert hr.unit == "/min"
    assert hr.patient_ref == "Patient/patient-001"
    assert hr.encounter_ref == "Encounter/encounter-001"


def test_observation_has_effective_datetime(sample_bundle_df):
    observations = extract_observations(sample_bundle_df)
    for row in observations.collect():
        assert row.effective_datetime is not None
