"""Tests for OMOP CDM mapper — verifies correct concept_id resolution and schema."""

import json

from src.data_generator.fhir_templates import generate_clinical_bundle
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


def test_map_to_person_gender_concept_id(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    person = map_to_person(spark, patients)

    row = person.first()
    assert row.gender_concept_id == 8507  # male
    assert row.gender_source_value == "male"


def test_map_to_person_birth_fields(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    person = map_to_person(spark, patients)

    row = person.first()
    assert row.year_of_birth == 1985
    assert row.month_of_birth == 3
    assert row.day_of_birth == 15


def test_map_to_person_mrn_as_source_value(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    person = map_to_person(spark, patients)

    row = person.first()
    assert row.person_source_value == "MRN-12345678"


def test_map_to_person_defaults(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    person = map_to_person(spark, patients)

    row = person.first()
    assert row.race_concept_id == 0
    assert row.ethnicity_concept_id == 0


def test_map_to_visit_occurrence_concept_id(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)

    row = visits.first()
    assert row.visit_concept_id == 9202  # AMB = Outpatient
    assert row.visit_source_value == "AMB"


def test_map_to_visit_occurrence_dates(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)

    row = visits.first()
    assert row.visit_start_date is not None
    assert row.visit_end_date is not None


def test_map_to_measurement_concept_ids(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    observations = extract_observations(sample_bundle_df)

    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)
    measurements = map_to_measurement(spark, observations, person, visits)

    rows = {row.measurement_source_value: row for row in measurements.collect()}

    # Heart Rate: LOINC 8867-4 → OMOP 3027018
    assert rows["8867-4"].measurement_concept_id == 3027018
    assert rows["8867-4"].value_as_number == 72.0

    # Systolic BP: LOINC 8480-6 → OMOP 3004249
    assert rows["8480-6"].measurement_concept_id == 3004249
    assert rows["8480-6"].value_as_number == 120.0

    # Diastolic BP: LOINC 8462-4 → OMOP 3012888
    assert rows["8462-4"].measurement_concept_id == 3012888
    assert rows["8462-4"].value_as_number == 80.0


def test_map_to_measurement_type_concept_id(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    observations = extract_observations(sample_bundle_df)

    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)
    measurements = map_to_measurement(spark, observations, person, visits)

    for row in measurements.collect():
        assert row.measurement_type_concept_id == 32817  # EHR


def test_map_to_measurement_person_id_resolved(spark, sample_bundle_df):
    patients = extract_patients(sample_bundle_df)
    encounters = extract_encounters(sample_bundle_df)
    observations = extract_observations(sample_bundle_df)

    person = map_to_person(spark, patients)
    visits = map_to_visit_occurrence(spark, encounters, person)
    measurements = map_to_measurement(spark, observations, person, visits)

    person_ids = {row.person_id for row in person.collect()}
    for row in measurements.collect():
        assert row.person_id in person_ids


def _omop_keys(spark, bundle_df):
    person = map_to_person(spark, extract_patients(bundle_df))
    visits = map_to_visit_occurrence(spark, extract_encounters(bundle_df), person)
    measurements = map_to_measurement(spark, extract_observations(bundle_df), person, visits)
    return (
        sorted(r.person_id for r in person.collect()),
        sorted(r.visit_occurrence_id for r in visits.collect()),
        sorted(r.measurement_id for r in measurements.collect()),
    )


def test_surrogate_keys_are_stable_across_runs(spark, sample_bundle_df):
    first_run = _omop_keys(spark, sample_bundle_df)
    second_run = _omop_keys(spark, sample_bundle_df)

    assert first_run == second_run
    assert all(key >= 0 for keys in first_run for key in keys)


def test_surrogate_keys_unique_across_separate_bundles(spark, tmp_path):
    keys = []
    for i in range(2):
        path = tmp_path / f"bundle_{i}.json"
        path.write_text(json.dumps(generate_clinical_bundle(num_observations=6)))
        keys.append(_omop_keys(spark, spark.read.option("multiline", "true").json(str(path))))

    for table_keys in zip(*keys):
        combined = table_keys[0] + table_keys[1]
        assert len(combined) == len(set(combined))
