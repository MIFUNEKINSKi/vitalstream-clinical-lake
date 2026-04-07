"""Tests for FHIR Bundle structural validator."""

from src.validation_lambda.fhir_validator import validate_bundle


def test_valid_bundle_passes(sample_bundle_dict):
    errors = validate_bundle(sample_bundle_dict)
    assert errors == []


def test_invalid_bundle_catches_missing_fields(invalid_bundle_dict):
    errors = validate_bundle(invalid_bundle_dict)
    assert len(errors) > 0
    error_text = " ".join(errors)
    assert "gender" in error_text
    assert "birthDate" in error_text


def test_wrong_resource_type():
    errors = validate_bundle({"resourceType": "Patient"})
    assert any("Expected resourceType 'Bundle'" in e for e in errors)


def test_wrong_bundle_type():
    errors = validate_bundle({"resourceType": "Bundle", "type": "collection", "entry": []})
    assert any("Expected Bundle type 'transaction'" in e for e in errors)


def test_empty_entries():
    errors = validate_bundle({"resourceType": "Bundle", "type": "transaction", "entry": []})
    assert any("no entries" in e for e in errors)


def test_missing_observation_value():
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "p1",
                    "gender": "female",
                    "birthDate": "1990-01-01",
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "e1",
                    "status": "finished",
                    "class": {"code": "AMB"},
                    "period": {"start": "2025-01-01"},
                    "subject": {"reference": "Patient/p1"},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "o1",
                    "status": "final",
                    "code": {"coding": [{"code": "8867-4"}]},
                    "subject": {"reference": "Patient/p1"},
                    # Missing valueQuantity
                }
            },
        ],
    }
    errors = validate_bundle(bundle)
    assert any("valueQuantity.value" in e for e in errors)


def test_no_patient_in_bundle():
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "e1",
                    "status": "finished",
                    "class": {"code": "AMB"},
                    "period": {"start": "2025-01-01"},
                    "subject": {"reference": "Patient/p1"},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "o1",
                    "status": "final",
                    "code": {"coding": [{"code": "8867-4"}]},
                    "subject": {"reference": "Patient/p1"},
                    "valueQuantity": {"value": 72},
                }
            },
        ],
    }
    errors = validate_bundle(bundle)
    assert any("no Patient" in e for e in errors)
