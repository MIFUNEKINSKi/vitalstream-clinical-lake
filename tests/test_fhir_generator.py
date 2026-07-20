"""Tests for FHIR R4 data generator."""

from src.data_generator.fhir_templates import (
    create_bundle,
    create_encounter,
    create_observation,
    create_patient,
    generate_clinical_bundle,
)
from src.data_generator.vocabulary import VITAL_SIGNS


def test_create_patient_has_required_fields():
    patient = create_patient()
    assert patient["resourceType"] == "Patient"
    assert "id" in patient
    assert patient["gender"] in ("male", "female")
    assert "birthDate" in patient
    assert len(patient["identifier"]) > 0
    assert patient["identifier"][0]["value"].startswith("MRN-")


def test_create_encounter_references_patient():
    encounter = create_encounter("patient-123")
    assert encounter["resourceType"] == "Encounter"
    assert encounter["subject"]["reference"] == "Patient/patient-123"
    assert encounter["status"] == "finished"
    assert encounter["class"]["code"] in ("AMB", "IMP")
    assert "start" in encounter["period"]
    assert "end" in encounter["period"]


def test_create_observation_has_loinc_and_value():
    vital_sign = VITAL_SIGNS[0]  # Heart Rate
    obs = create_observation("patient-123", "encounter-456", vital_sign)

    assert obs["resourceType"] == "Observation"
    assert obs["status"] == "final"
    assert obs["subject"]["reference"] == "Patient/patient-123"
    assert obs["encounter"]["reference"] == "Encounter/encounter-456"

    coding = obs["code"]["coding"][0]
    assert coding["system"] == "http://loinc.org"
    assert coding["code"] == vital_sign.loinc_code

    qty = obs["valueQuantity"]
    assert vital_sign.min_realistic <= qty["value"] <= vital_sign.max_realistic
    assert qty["unit"] == vital_sign.unit_ucum


def test_create_bundle_wraps_resources():
    patient = create_patient()
    encounter = create_encounter(patient["id"])
    bundle = create_bundle([patient, encounter])

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "transaction"
    assert len(bundle["entry"]) == 2

    for entry in bundle["entry"]:
        assert "fullUrl" in entry
        assert "resource" in entry
        assert "request" in entry
        assert entry["request"]["method"] == "POST"


def test_generate_clinical_bundle_produces_complete_bundle():
    bundle = generate_clinical_bundle(num_observations=4)

    resource_types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert resource_types.count("Patient") == 1
    assert resource_types.count("Encounter") == 1
    assert resource_types.count("Observation") == 4


def test_generate_clinical_bundle_default_observations():
    bundle = generate_clinical_bundle()
    obs_count = sum(
        1 for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"
    )
    assert 3 <= obs_count <= 6


def test_all_observations_reference_same_patient():
    bundle = generate_clinical_bundle(num_observations=3)

    patient_id = None
    for entry in bundle["entry"]:
        r = entry["resource"]
        if r["resourceType"] == "Patient":
            patient_id = r["id"]

    for entry in bundle["entry"]:
        r = entry["resource"]
        if r["resourceType"] == "Observation":
            assert r["subject"]["reference"] == f"Patient/{patient_id}"
