"""Pure functions that construct FHIR R4 resource dictionaries.

Each function returns a plain dict matching the HL7 FHIR R4 JSON spec.
No side effects, no I/O — designed for easy testing and composition.
"""

from __future__ import annotations

import uuid
import random
from datetime import datetime, timedelta

from faker import Faker

from src.data_generator.vocabulary import VITAL_SIGNS, VitalSignDef

fake = Faker()


def create_patient() -> dict:
    """Create a FHIR R4 Patient resource with realistic demographics."""
    gender = random.choice(["male", "female"])
    birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90)

    return {
        "resourceType": "Patient",
        "id": str(uuid.uuid4()),
        "identifier": [
            {
                "system": "http://hospital.example.org/mrn",
                "value": f"MRN-{fake.unique.random_number(digits=8)}",
            }
        ],
        "name": [
            {
                "family": fake.last_name(),
                "given": [fake.first_name()],
            }
        ],
        "gender": gender,
        "birthDate": birth_date.isoformat(),
        "address": [
            {
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postalCode": fake.zipcode(),
            }
        ],
    }


def create_encounter(patient_id: str) -> dict:
    """Create a FHIR R4 Encounter resource linked to a patient."""
    encounter_class = random.choice(["AMB", "IMP"])
    start = fake.date_time_between(start_date="-1y", end_date="now")
    end = start + timedelta(hours=random.randint(1, 48))

    return {
        "resourceType": "Encounter",
        "id": str(uuid.uuid4()),
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": encounter_class,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    }


def create_observation(
    patient_id: str,
    encounter_id: str,
    vital_sign: VitalSignDef,
    effective_datetime: Optional[datetime] = None,
) -> dict:
    """Create a FHIR R4 Observation resource for a vital sign measurement."""
    if effective_datetime is None:
        effective_datetime = fake.date_time_between(start_date="-1y", end_date="now")

    value = round(
        random.uniform(vital_sign.min_realistic, vital_sign.max_realistic), 1
    )

    return {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": vital_sign.loinc_code,
                    "display": vital_sign.name,
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "effectiveDateTime": effective_datetime.isoformat(),
        "valueQuantity": {
            "value": value,
            "unit": vital_sign.unit_ucum,
            "system": "http://unitsofmeasure.org",
            "code": vital_sign.unit_ucum,
        },
    }


def create_bundle(resources: list) -> dict:
    """Wrap FHIR resources into a FHIR R4 transaction Bundle."""
    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "transaction",
        "entry": [
            {
                "fullUrl": f"urn:uuid:{resource['id']}",
                "resource": resource,
                "request": {
                    "method": "POST",
                    "url": resource["resourceType"],
                },
            }
            for resource in resources
        ],
    }


def generate_clinical_bundle(num_observations: Optional[int] = None) -> dict:
    """Generate a complete clinical bundle with patient, encounter, and observations.

    Args:
        num_observations: Number of vital sign observations to include.
            Defaults to random 3-6.

    Returns:
        A FHIR R4 Bundle containing one Patient, one Encounter,
        and multiple Observation resources.
    """
    if num_observations is None:
        num_observations = random.randint(3, 6)

    patient = create_patient()
    encounter = create_encounter(patient["id"])

    selected_vitals = random.sample(
        VITAL_SIGNS, min(num_observations, len(VITAL_SIGNS))
    )

    observations = [
        create_observation(patient["id"], encounter["id"], vs)
        for vs in selected_vitals
    ]

    return create_bundle([patient, encounter] + observations)  # type: ignore[arg-type]
