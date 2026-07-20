"""Regenerate sample_outputs/ by running the real VitalStream pipeline locally.

Usage:
    make samples
    # or: python scripts/regenerate_sample_outputs.py

Produces person.csv, visit_occurrence.csv, measurement.csv and
data_quality_report.json exactly as the generator -> parser -> mapper -> DQ
chain emits them, so the samples cannot drift from the code by hand-editing.
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
from src.glue_jobs.fhir_parser import (  # noqa: E402
    extract_encounters,
    extract_observations,
    extract_patients,
)
from src.glue_jobs.omop_mapper import (  # noqa: E402
    map_to_measurement,
    map_to_person,
    map_to_visit_occurrence,
)

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

        person = map_to_person(spark, extract_patients(bundle_df))
        visits = map_to_visit_occurrence(spark, extract_encounters(bundle_df), person)
        measurements = map_to_measurement(spark, extract_observations(bundle_df), person, visits)

        # Same projections the deployed ETL job writes to the curated zone
        person_out = person.drop("patient_fhir_id").cache()
        visits_out = visits.drop("encounter_fhir_id").cache()
        measurements_out = measurements.cache()

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

    spark.stop()


if __name__ == "__main__":
    main()
