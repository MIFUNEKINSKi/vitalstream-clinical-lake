"""Structural validation for FHIR R4 Bundles.

Lightweight checks — no external FHIR library dependency.
Validates resource structure, required fields, and reference integrity.
"""

from __future__ import annotations


class ValidationError(Exception):
    """Raised when a FHIR Bundle fails structural validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"FHIR validation failed: {len(errors)} error(s)")


def validate_bundle(bundle: dict) -> list[str]:
    """Validate a FHIR R4 Bundle structure.

    Returns a list of error strings. Empty list means valid.
    """
    errors = []

    if bundle.get("resourceType") != "Bundle":
        errors.append(f"Expected resourceType 'Bundle', got '{bundle.get('resourceType')}'")
        return errors

    if bundle.get("type") != "transaction":
        errors.append(f"Expected Bundle type 'transaction', got '{bundle.get('type')}'")

    entries = bundle.get("entry", [])
    if not entries:
        errors.append("Bundle has no entries")
        return errors

    has_patient = False
    has_encounter = False
    has_observation = False

    for i, entry in enumerate(entries):
        resource = entry.get("resource")
        if not resource:
            errors.append(f"Entry {i}: missing 'resource'")
            continue

        rt = resource.get("resourceType")
        if rt == "Patient":
            has_patient = True
            errors.extend(_validate_patient(resource, i))
        elif rt == "Encounter":
            has_encounter = True
            errors.extend(_validate_encounter(resource, i))
        elif rt == "Observation":
            has_observation = True
            errors.extend(_validate_observation(resource, i))

    if not has_patient:
        errors.append("Bundle contains no Patient resource")
    if not has_encounter:
        errors.append("Bundle contains no Encounter resource")
    if not has_observation:
        errors.append("Bundle contains no Observation resource")

    return errors


def _validate_patient(resource: dict, index: int) -> list[str]:
    """Validate required Patient fields."""
    errors = []
    prefix = f"Entry {index} (Patient)"

    if not resource.get("id"):
        errors.append(f"{prefix}: missing 'id'")
    if not resource.get("gender"):
        errors.append(f"{prefix}: missing 'gender'")
    if not resource.get("birthDate"):
        errors.append(f"{prefix}: missing 'birthDate'")

    return errors


def _validate_encounter(resource: dict, index: int) -> list[str]:
    """Validate required Encounter fields."""
    errors = []
    prefix = f"Entry {index} (Encounter)"

    if not resource.get("id"):
        errors.append(f"{prefix}: missing 'id'")
    if not resource.get("status"):
        errors.append(f"{prefix}: missing 'status'")

    enc_class = resource.get("class", {})
    if not enc_class.get("code"):
        errors.append(f"{prefix}: missing 'class.code'")

    period = resource.get("period", {})
    if not period.get("start"):
        errors.append(f"{prefix}: missing 'period.start'")

    subject = resource.get("subject", {})
    if not subject.get("reference"):
        errors.append(f"{prefix}: missing 'subject.reference'")

    return errors


def _validate_observation(resource: dict, index: int) -> list[str]:
    """Validate required Observation fields."""
    errors = []
    prefix = f"Entry {index} (Observation)"

    if not resource.get("id"):
        errors.append(f"{prefix}: missing 'id'")
    if not resource.get("status"):
        errors.append(f"{prefix}: missing 'status'")

    code = resource.get("code", {})
    codings = code.get("coding", [])
    if not codings or not codings[0].get("code"):
        errors.append(f"{prefix}: missing 'code.coding[0].code'")

    subject = resource.get("subject", {})
    if not subject.get("reference"):
        errors.append(f"{prefix}: missing 'subject.reference'")

    vq = resource.get("valueQuantity", {})
    if vq.get("value") is None:
        errors.append(f"{prefix}: missing 'valueQuantity.value'")

    return errors
