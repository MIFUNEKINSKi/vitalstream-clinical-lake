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

# OMOP type concept IDs
MEASUREMENT_TYPE_CONCEPT_ID = 32817  # EHR
VISIT_TYPE_CONCEPT_ID = 32817  # EHR

# FHIR resource types
FHIR_PATIENT = "Patient"
FHIR_ENCOUNTER = "Encounter"
FHIR_OBSERVATION = "Observation"
FHIR_BUNDLE = "Bundle"
