"""Generate dbt/seeds/vital_sign_reference.csv from vocabulary.py VITAL_SIGNS.

Usage:
    python scripts/generate_dbt_seed.py

Keeps src/data_generator/vocabulary.py the single source of truth for
vital-sign concept_ids and thresholds: the dbt models and tests consume this
seed rather than hardcoding their own copies.
"""

import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from src.data_generator.vocabulary import VITAL_SIGNS  # noqa: E402

OUT_PATH = os.path.join(REPO, "dbt", "seeds", "vital_sign_reference.csv")

COLUMNS = [
    "loinc_code",
    "omop_concept_id",
    "vital_sign",
    "abnormal_flag",
    "unit_ucum",
    "plausible_min",
    "plausible_max",
    "alert_min",
    "alert_max",
]


def fmt(value: float) -> str:
    return f"{value:g}"


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for vs in VITAL_SIGNS:
            writer.writerow([
                vs.loinc_code,
                vs.omop_concept_id,
                vs.name,
                "abnormal_" + vs.name.lower().replace(" ", "_"),
                vs.unit_ucum,
                fmt(vs.min_plausible),
                fmt(vs.max_plausible),
                fmt(vs.min_alert),
                fmt(vs.max_alert),
            ])
    print(f"wrote {OUT_PATH} ({len(VITAL_SIGNS)} vital signs)")


if __name__ == "__main__":
    main()
