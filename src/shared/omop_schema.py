"""PySpark StructType definitions for OMOP CDM v5.4 tables.

Defines the exact column names, data types, and nullable constraints
for each OMOP table produced by the VitalStream pipeline.
"""

from pyspark.sql.types import (
    IntegerType,
    LongType,
    FloatType,
    StringType,
    DateType,
    TimestampType,
    StructField,
    StructType,
)

PERSON_SCHEMA = StructType([
    StructField("person_id", LongType(), nullable=False),
    StructField("gender_concept_id", IntegerType(), nullable=False),
    StructField("year_of_birth", IntegerType(), nullable=False),
    StructField("month_of_birth", IntegerType(), nullable=True),
    StructField("day_of_birth", IntegerType(), nullable=True),
    StructField("birth_datetime", TimestampType(), nullable=True),
    StructField("race_concept_id", IntegerType(), nullable=False),
    StructField("ethnicity_concept_id", IntegerType(), nullable=False),
    StructField("person_source_value", StringType(), nullable=True),
    StructField("gender_source_value", StringType(), nullable=True),
])

VISIT_OCCURRENCE_SCHEMA = StructType([
    StructField("visit_occurrence_id", LongType(), nullable=False),
    StructField("person_id", LongType(), nullable=False),
    StructField("visit_concept_id", IntegerType(), nullable=False),
    StructField("visit_start_date", DateType(), nullable=False),
    StructField("visit_start_datetime", TimestampType(), nullable=True),
    StructField("visit_end_date", DateType(), nullable=True),
    StructField("visit_end_datetime", TimestampType(), nullable=True),
    StructField("visit_type_concept_id", IntegerType(), nullable=False),
    StructField("visit_source_value", StringType(), nullable=True),
])

MEASUREMENT_SCHEMA = StructType([
    StructField("measurement_id", LongType(), nullable=False),
    StructField("person_id", LongType(), nullable=False),
    StructField("measurement_concept_id", IntegerType(), nullable=False),
    StructField("measurement_date", DateType(), nullable=False),
    StructField("measurement_datetime", TimestampType(), nullable=True),
    StructField("measurement_type_concept_id", IntegerType(), nullable=False),
    StructField("value_as_number", FloatType(), nullable=True),
    StructField("unit_concept_id", IntegerType(), nullable=True),
    StructField("unit_source_value", StringType(), nullable=True),
    StructField("measurement_source_value", StringType(), nullable=True),
    StructField("visit_occurrence_id", LongType(), nullable=True),
])

OBSERVATION_SCHEMA = StructType([
    StructField("observation_id", LongType(), nullable=False),
    StructField("person_id", LongType(), nullable=False),
    StructField("observation_concept_id", IntegerType(), nullable=False),
    StructField("observation_date", DateType(), nullable=False),
    StructField("observation_datetime", TimestampType(), nullable=True),
    StructField("observation_type_concept_id", IntegerType(), nullable=False),
    StructField("value_as_string", StringType(), nullable=True),
    StructField("value_as_number", FloatType(), nullable=True),
    StructField("observation_source_value", StringType(), nullable=True),
    StructField("visit_occurrence_id", LongType(), nullable=True),
])
