"""Generate dbt seeds from vocabulary.py.

Usage:
    python scripts/generate_dbt_seed.py

Writes vital_sign_reference.csv (from VITAL_SIGNS) and
pcornet_value_sets.csv (from the PCORNET_* permissible-value sets).
Keeps src/data_generator/vocabulary.py the single source of truth:
the dbt models and tests consume these seeds rather than hardcoding
their own copies.
"""

import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from src.data_generator.vocabulary import (  # noqa: E402
    PCORNET_ENC_TYPE_VALUES,
    PCORNET_OBSCLIN_TYPE_VALUES,
    PCORNET_SEX_VALUES,
    VITAL_SIGNS,
)

OUT_PATH = os.path.join(REPO, "dbt", "seeds", "vital_sign_reference.csv")
PCORNET_OUT_PATH = os.path.join(REPO, "dbt", "seeds", "pcornet_value_sets.csv")

PCORNET_VALUE_SETS = [
    ("demographic", "sex", PCORNET_SEX_VALUES),
    ("encounter", "enc_type", PCORNET_ENC_TYPE_VALUES),
    ("obs_clin", "obsclin_type", PCORNET_OBSCLIN_TYPE_VALUES),
]

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

    with open(PCORNET_OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["table_name", "column_name", "allowed_value"])
        for table_name, column_name, allowed in PCORNET_VALUE_SETS:
            for value in sorted(allowed):
                writer.writerow([table_name, column_name, value])
    print(f"wrote {PCORNET_OUT_PATH} ({len(PCORNET_VALUE_SETS)} value sets)")


if __name__ == "__main__":
    main()
