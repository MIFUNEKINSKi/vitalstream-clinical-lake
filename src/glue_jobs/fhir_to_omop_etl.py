"""AWS Glue ETL job: FHIR R4 Bundles → OMOP CDM v5.4 Parquet tables.

Entry point for the Glue PySpark job. Thin orchestrator over
fhir_parser and omop_mapper modules.

Usage (Glue job arguments):
    --source_path   s3://landing-zone/raw/
    --target_path   s3://curated-zone/omop/
    --JOB_NAME      vitalstream_fhir_to_omop
"""

import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

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


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "source_path", "target_path"])

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    source_path = args["source_path"]
    target_path = args["target_path"]

    print(f"Reading FHIR Bundles from {source_path}")
    bundle_df = read_fhir_bundles(spark, source_path)

    # Extract FHIR resources
    patients_df = extract_patients(bundle_df)
    encounters_df = extract_encounters(bundle_df)
    observations_df = extract_observations(bundle_df)

    print(f"Extracted: {patients_df.count()} patients, "
          f"{encounters_df.count()} encounters, "
          f"{observations_df.count()} observations")

    # Map to OMOP CDM
    person_df = map_to_person(spark, patients_df)
    visit_df = map_to_visit_occurrence(spark, encounters_df, person_df)
    measurement_df = map_to_measurement(spark, observations_df, person_df, visit_df)

    # Write partitioned Parquet to curated zone
    person_df.drop("patient_fhir_id").write.mode("overwrite").parquet(f"{target_path}/person/")
    visit_df.drop("encounter_fhir_id").write.mode("overwrite").parquet(f"{target_path}/visit_occurrence/")
    measurement_df.write.mode("overwrite").parquet(f"{target_path}/measurement/")

    print(f"Wrote OMOP tables to {target_path}")

    job.commit()


if __name__ == "__main__":
    main()
