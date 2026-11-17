"""Shared constants for VitalStream pipeline."""

# S3 path prefixes
RAW_PREFIX = "raw/"
CURATED_PREFIX = "curated/"
DQ_REPORTS_PREFIX = "dq_reports/"
ERRORS_PREFIX = "errors/"

# OMOP table names
PERSON_TABLE = "person"
VISIT_OCCURRENCE_TABLE = "visit_occurrence"
MEASUREMENT_TABLE = "measurement"
OBSERVATION_TABLE = "observation"



def ingest_partition_path(base_path: str, table: str, ingest_id: str) -> str:
    """Curated-zone folder for one table's rows from one source bundle.

    Each upload writes (and on a re-upload, overwrites) only its own partition,
    so concurrent runs never touch each other's data and DQ can read exactly
    the rows its own run produced.
    """
    return f"{base_path.rstrip('/')}/{table}/ingest_id={ingest_id}/"


# OMOP type concept IDs
MEASUREMENT_TYPE_CONCEPT_ID = 32817  # EHR
VISIT_TYPE_CONCEPT_ID = 32817  # EHR

# FHIR resource types
FHIR_PATIENT = "Patient"
FHIR_ENCOUNTER = "Encounter"
FHIR_OBSERVATION = "Observation"
FHIR_BUNDLE = "Bundle"

# PCORnet table names
DEMOGRAPHIC_TABLE = "demographic"
ENCOUNTER_TABLE = "encounter"
VITAL_TABLE = "vital"
OBS_CLIN_TABLE = "obs_clin"

# PCORnet fixed codes
PCORNET_NO_INFORMATION = "NI"
PCORNET_OTHER = "OT"
OBSCLIN_TYPE_LOINC = "LC"
VITAL_SOURCE_HEALTHCARE = "HC"  # Healthcare delivery setting
OBSCLIN_SOURCE_HEALTHCARE = "HC"
RESULT_MODIFIER_EQUAL = "EQ"
