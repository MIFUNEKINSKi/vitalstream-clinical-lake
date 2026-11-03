"""AWS Glue ETL job: FHIR R4 Bundles → OMOP CDM v5.4 and PCORnet CDM v6.1 Parquet tables.

Entry point for the Glue PySpark job. Thin orchestrator over fhir_parser,
omop_mapper and pcornet_mapper: the bundles are parsed once and both common
data models are built from the same parsed DataFrames.

Usage (Glue job arguments):
    --source_path           s3://landing-zone/raw/
    --target_path           s3://curated-zone/omop/
    --pcornet_target_path   s3://curated-zone/pcornet/   (optional; omit to write OMOP only)
    --JOB_NAME              vitalstream_fhir_to_omop
"""

import sys

from pyspark.sql import DataFrame, SparkSession

from src.glue_jobs.fhir_parser import (
    extract_encounters,
    extract_observations,
    extract_patients,
    read_fhir_bundles,
)
from src.glue_jobs.omop_mapper import (
    map_to_measurement,
    map_to_person,
    map_to_visit_occurrence,
)
from src.glue_jobs.pcornet_mapper import (
    map_to_demographic,
    map_to_encounter,
    map_to_obs_clin,
    map_to_vital,
)
from src.shared.constants import (
    DEMOGRAPHIC_TABLE,
    ENCOUNTER_TABLE,
    MEASUREMENT_TABLE,
    OBS_CLIN_TABLE,
    PERSON_TABLE,
    VISIT_OCCURRENCE_TABLE,
    VITAL_TABLE,
)


def build_cdm_tables(spark: SparkSession, bundle_df: DataFrame, include_pcornet: bool = True) -> dict:
    """Parse FHIR Bundles once and map them to OMOP (and optionally PCORnet) tables.

    Returns {"omop": {table: df}, "pcornet": {table: df}}; the "pcornet" key is
    absent when include_pcornet is False. OMOP frames still carry the
    patient_fhir_id / encounter_fhir_id helper columns; they are dropped at write time.
    """
    patients_df = extract_patients(bundle_df)
    encounters_df = extract_encounters(bundle_df)
    observations_df = extract_observations(bundle_df)

    person_df = map_to_person(spark, patients_df)
    visit_df = map_to_visit_occurrence(spark, encounters_df, person_df)
    measurement_df = map_to_measurement(spark, observations_df, person_df, visit_df)

    tables = {
        "omop": {
            PERSON_TABLE: person_df,
            VISIT_OCCURRENCE_TABLE: visit_df,
            MEASUREMENT_TABLE: measurement_df,
        },
    }

    if include_pcornet:
        demographic_df = map_to_demographic(spark, patients_df)
        encounter_df = map_to_encounter(spark, encounters_df, demographic_df)
        tables["pcornet"] = {
            DEMOGRAPHIC_TABLE: demographic_df,
            ENCOUNTER_TABLE: encounter_df,
            VITAL_TABLE: map_to_vital(spark, observations_df, demographic_df, encounter_df),
            OBS_CLIN_TABLE: map_to_obs_clin(spark, observations_df, demographic_df, encounter_df),
        }

    return tables


def main():
    # awsglue is only available inside the Glue runtime; import here so the
    # module stays importable by local tests.
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions
    from pyspark.context import SparkContext

    # getResolvedOptions fails on missing arguments, so only ask for the
    # optional PCORnet target when the job was given one.
    write_pcornet = "--pcornet_target_path" in sys.argv
    arg_names = ["JOB_NAME", "source_path", "target_path"] + (["pcornet_target_path"] if write_pcornet else [])
    args = getResolvedOptions(sys.argv, arg_names)

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    source_path = args["source_path"]
    target_path = args["target_path"]

    print(f"Reading FHIR Bundles from {source_path}")
    bundle_df = read_fhir_bundles(spark, source_path)

    tables = build_cdm_tables(spark, bundle_df, include_pcornet=write_pcornet)
    omop = tables["omop"]

    # Write partitioned Parquet to curated zone
    omop[PERSON_TABLE].drop("patient_fhir_id").write.mode("overwrite").parquet(f"{target_path}/person/")
    omop[VISIT_OCCURRENCE_TABLE].drop("encounter_fhir_id").write.mode("overwrite").parquet(
        f"{target_path}/visit_occurrence/"
    )
    omop[MEASUREMENT_TABLE].write.mode("overwrite").parquet(f"{target_path}/measurement/")

    print(f"Wrote OMOP tables to {target_path}")

    if write_pcornet:
        pcornet_target_path = args["pcornet_target_path"]
        for table_name, df in tables["pcornet"].items():
            df.write.mode("overwrite").parquet(f"{pcornet_target_path}/{table_name}/")
            print(f"  PCORnet {table_name.upper()}: {df.count()} rows")
        print(f"Wrote PCORnet tables to {pcornet_target_path}")

    job.commit()


if __name__ == "__main__":
    main()
