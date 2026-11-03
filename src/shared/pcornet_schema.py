"""PySpark StructType definitions for PCORnet CDM v6.1 tables.

Defines the column names, data types, and nullable constraints for the subset
of each PCORnet table produced by the VitalStream pipeline. Column names follow
the PCORnet specification (upper case); times are "HH:MM" strings per the spec.
"""

from pyspark.sql.types import (
    DateType,
    DoubleType,
    StringType,
    StructField,
    StructType,
)

DEMOGRAPHIC_SCHEMA = StructType([
    StructField("PATID", StringType(), nullable=False),
    StructField("BIRTH_DATE", DateType(), nullable=True),
    StructField("BIRTH_TIME", StringType(), nullable=True),
    StructField("SEX", StringType(), nullable=False),
    StructField("HISPANIC", StringType(), nullable=True),
    StructField("RACE", StringType(), nullable=True),
    StructField("RAW_SEX", StringType(), nullable=True),
    StructField("RAW_HISPANIC", StringType(), nullable=True),
    StructField("RAW_RACE", StringType(), nullable=True),
])

ENCOUNTER_SCHEMA = StructType([
    StructField("ENCOUNTERID", StringType(), nullable=False),
    StructField("PATID", StringType(), nullable=False),
    StructField("ADMIT_DATE", DateType(), nullable=False),
    StructField("ADMIT_TIME", StringType(), nullable=True),
    StructField("DISCHARGE_DATE", DateType(), nullable=True),
    StructField("DISCHARGE_TIME", StringType(), nullable=True),
    StructField("ENC_TYPE", StringType(), nullable=False),
    StructField("RAW_ENC_TYPE", StringType(), nullable=True),
])

VITAL_SCHEMA = StructType([
    StructField("VITALID", StringType(), nullable=False),
    StructField("PATID", StringType(), nullable=False),
    StructField("ENCOUNTERID", StringType(), nullable=True),
    StructField("MEASURE_DATE", DateType(), nullable=False),
    StructField("MEASURE_TIME", StringType(), nullable=True),
    StructField("VITAL_SOURCE", StringType(), nullable=False),
    StructField("HT", DoubleType(), nullable=True),
    StructField("WT", DoubleType(), nullable=True),
    StructField("DIASTOLIC", DoubleType(), nullable=True),
    StructField("SYSTOLIC", DoubleType(), nullable=True),
    StructField("ORIGINAL_BMI", DoubleType(), nullable=True),
    StructField("BP_POSITION", StringType(), nullable=True),
    StructField("RAW_DIASTOLIC", StringType(), nullable=True),
    StructField("RAW_SYSTOLIC", StringType(), nullable=True),
    StructField("RAW_BP_POSITION", StringType(), nullable=True),
])

OBS_CLIN_SCHEMA = StructType([
    StructField("OBSCLINID", StringType(), nullable=False),
    StructField("PATID", StringType(), nullable=False),
    StructField("ENCOUNTERID", StringType(), nullable=True),
    StructField("OBSCLIN_START_DATE", DateType(), nullable=False),
    StructField("OBSCLIN_START_TIME", StringType(), nullable=True),
    StructField("OBSCLIN_TYPE", StringType(), nullable=False),
    StructField("OBSCLIN_CODE", StringType(), nullable=False),
    StructField("OBSCLIN_RESULT_NUM", DoubleType(), nullable=True),
    StructField("OBSCLIN_RESULT_MODIFIER", StringType(), nullable=True),
    StructField("OBSCLIN_RESULT_UNIT", StringType(), nullable=True),
    StructField("OBSCLIN_SOURCE", StringType(), nullable=True),
    StructField("RAW_OBSCLIN_NAME", StringType(), nullable=True),
    StructField("RAW_OBSCLIN_CODE", StringType(), nullable=True),
    StructField("RAW_OBSCLIN_TYPE", StringType(), nullable=True),
    StructField("RAW_OBSCLIN_RESULT", StringType(), nullable=True),
    StructField("RAW_OBSCLIN_UNIT", StringType(), nullable=True),
])
