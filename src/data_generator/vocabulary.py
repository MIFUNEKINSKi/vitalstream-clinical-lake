"""LOINC-to-OMOP vocabulary mappings and clinical reference data.

Concept IDs sourced from OHDSI OMOP CDM v5.4 standardized vocabularies.
LOINC codes from https://loinc.org for vital sign observations.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VitalSignDef:
    """Definition of a vital sign with FHIR and OMOP mappings.

    min/max_realistic bound the synthetic generator's output;
    min/max_plausible bound what the DQ range checks accept as
    clinically possible (anything outside is a data error);
    min/max_alert bound the normal range used by dashboard
    abnormal-vital flags (outside = clinically notable, not a data error).
    """

    name: str
    loinc_code: str
    omop_concept_id: int
    unit_ucum: str
    min_realistic: float
    max_realistic: float
    min_plausible: float
    max_plausible: float
    min_alert: float
    max_alert: float


# Six vital signs with LOINC → OMOP concept_id mappings
VITAL_SIGNS = [
    VitalSignDef(
        name="Heart Rate",
        loinc_code="8867-4",
        omop_concept_id=3027018,
        unit_ucum="/min",
        min_realistic=60,
        max_realistic=100,
        min_plausible=20,
        max_plausible=300,
        min_alert=50,
        max_alert=120,
    ),
    VitalSignDef(
        name="Systolic Blood Pressure",
        loinc_code="8480-6",
        omop_concept_id=3004249,
        unit_ucum="mm[Hg]",
        min_realistic=90,
        max_realistic=180,
        min_plausible=50,
        max_plausible=300,
        min_alert=90,
        max_alert=140,
    ),
    VitalSignDef(
        name="Diastolic Blood Pressure",
        loinc_code="8462-4",
        omop_concept_id=3012888,
        unit_ucum="mm[Hg]",
        min_realistic=60,
        max_realistic=120,
        min_plausible=20,
        max_plausible=200,
        min_alert=60,
        max_alert=90,
    ),
    VitalSignDef(
        name="Body Temperature",
        loinc_code="8310-5",
        omop_concept_id=3020891,
        unit_ucum="Cel",
        min_realistic=36.1,
        max_realistic=38.5,
        min_plausible=30,
        max_plausible=45,
        min_alert=36,
        max_alert=38,
    ),
    VitalSignDef(
        name="Respiratory Rate",
        loinc_code="9279-1",
        omop_concept_id=3024171,
        unit_ucum="/min",
        min_realistic=12,
        max_realistic=22,
        min_plausible=4,
        max_plausible=60,
        min_alert=12,
        max_alert=24,
    ),
    VitalSignDef(
        name="Oxygen Saturation",
        loinc_code="2708-6",
        omop_concept_id=3016502,
        unit_ucum="%",
        min_realistic=92,
        max_realistic=100,
        min_plausible=50,
        max_plausible=100,
        min_alert=95,
        max_alert=100,
    ),
]

# LOINC code → OMOP concept_id lookup
LOINC_TO_OMOP = {vs.loinc_code: vs.omop_concept_id for vs in VITAL_SIGNS}

# LOINC code → VitalSignDef lookup
LOINC_TO_VITAL_SIGN = {vs.loinc_code: vs for vs in VITAL_SIGNS}

# FHIR gender → OMOP gender_concept_id
GENDER_CONCEPT_MAP = {
    "male": 8507,
    "female": 8532,
    "other": 0,
    "unknown": 0,
}

# FHIR Encounter class → OMOP visit_concept_id
VISIT_CONCEPT_MAP = {
    "AMB": 9202,   # Outpatient Visit
    "IMP": 9201,   # Inpatient Visit
    "EMER": 9203,  # Emergency Room Visit
}
