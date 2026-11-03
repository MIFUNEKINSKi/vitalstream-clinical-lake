"""Regenerate sample_outputs/ by running the real VitalStream pipeline locally.

Usage:
    make samples
    # or: python scripts/regenerate_sample_outputs.py

Produces person.csv, visit_occurrence.csv, measurement.csv and
data_quality_report.json (OMOP), plus pcornet/{demographic,encounter,vital,
obs_clin}.csv and pcornet/pcornet_data_quality_report.json, exactly as the
generator -> parser -> mapper -> DQ chain emits them, so the samples cannot
drift from the code by hand-editing. Both models come from one
build_cdm_tables call, the same function the Glue ETL job runs.
"""

import csv
import json
import os
import random
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
# Pin Spark workers to this interpreter (required on Windows).
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from faker import Faker  # noqa: E402
from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402

from src.data_generator.fhir_templates import generate_clinical_bundle  # noqa: E402
from src.glue_jobs.data_quality import run_all_checks  # noqa: E402
from src.glue_jobs.fhir_to_omop_etl import build_cdm_tables  # noqa: E402
from src.glue_jobs.pcornet_data_quality import run_all_pcornet_checks  # noqa: E402

random.seed(42)
Faker.seed(42)

OUT_DIR = os.path.join(REPO, "sample_outputs")


def fmt(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{round(value, 1):g}"
    return str(value)


def write_csv(df, path):
    # Stringify timestamps Spark-side: collecting pre-1970 timestamps crashes
    # on Windows (datetime.fromtimestamp rejects negative epochs).
    df = df.select([
        F.date_format(F.col(name), "yyyy-MM-dd'T'HH:mm:ss").alias(name)
        if dtype == "timestamp" else F.col(name)
        for name, dtype in df.dtypes
    ])
    columns = df.columns
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in df.collect():
            writer.writerow([fmt(row[c]) for c in columns])
    print(f"wrote {path}")


def main():
    spark = (
        SparkSession.builder
        .master("local[1]")
        .appName("vitalstream-sample-regen")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )

    with tempfile.TemporaryDirectory() as bundle_dir:
        bundle_paths = []
        for i in range(3):
            bundle = generate_clinical_bundle()
            path = os.path.join(bundle_dir, f"bundle_{i}.json")
            with open(path, "w") as f:
                json.dump(bundle, f)
            bundle_paths.append(path)

        # Same reader options as read_fhir_bundles, but with explicit file
        # paths: directory listing needs winutils on Windows, single files don't.
        bundle_df = spark.read.option("multiline", "true").json(bundle_paths)

        tables = build_cdm_tables(spark, bundle_df)
        omop, pcornet = tables["omop"], tables["pcornet"]

        # Same projections the deployed ETL job writes to the curated zone
        person_out = omop["person"].drop("patient_fhir_id").cache()
        visits_out = omop["visit_occurrence"].drop("encounter_fhir_id").cache()
        measurements_out = omop["measurement"].cache()

        os.makedirs(OUT_DIR, exist_ok=True)
        write_csv(person_out.orderBy("person_id"), os.path.join(OUT_DIR, "person.csv"))
        write_csv(visits_out.orderBy("visit_occurrence_id"), os.path.join(OUT_DIR, "visit_occurrence.csv"))
        write_csv(measurements_out.orderBy("measurement_id"), os.path.join(OUT_DIR, "measurement.csv"))

        report = run_all_checks(person_out, visits_out, measurements_out)
        report_path = os.path.join(OUT_DIR, "data_quality_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {report_path}")
        print(f"DQ: {report['overall_result']} ({report['passed_checks']}/{report['total_checks']})")

        # PCORnet: cache so the surrogate VITALID is identical across the CSV and the DQ run
        pcornet_out = {name: df.cache() for name, df in pcornet.items()}
        pcornet_dir = os.path.join(OUT_DIR, "pcornet")
        os.makedirs(pcornet_dir, exist_ok=True)
        sort_keys = {
            "demographic": ["PATID"],
            "encounter": ["ENCOUNTERID"],
            "vital": ["PATID", "MEASURE_DATE", "MEASURE_TIME"],
            "obs_clin": ["OBSCLINID"],
        }
        for name, df in pcornet_out.items():
            write_csv(df.orderBy(*sort_keys[name]), os.path.join(pcornet_dir, f"{name}.csv"))

        pcornet_report = run_all_pcornet_checks(
            pcornet_out["demographic"], pcornet_out["encounter"], pcornet_out["vital"], pcornet_out["obs_clin"],
            omop=(person_out, visits_out, measurements_out),
        )
        pcornet_report_path = os.path.join(pcornet_dir, "pcornet_data_quality_report.json")
        with open(pcornet_report_path, "w", encoding="utf-8") as f:
            json.dump(pcornet_report, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"wrote {pcornet_report_path}")
        print(f"PCORnet DQ: {pcornet_report['overall_result']} "
              f"({pcornet_report['passed_checks']}/{pcornet_report['total_checks']})")

    spark.stop()


if __name__ == "__main__":
    main()
