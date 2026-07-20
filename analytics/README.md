# Athena Analytics

These SQL files assume the Glue Crawler has registered the curated OMOP Parquet outputs
and the DQ report table. Run them in Athena with the pipeline's Glue database selected
(default `vitalstream_db`; the name is `${var.project_name}_db` per the Terraform config) —
the queries use bare table names, so no per-file edits are needed.

| File | Purpose |
|------|---------|
| `patient_vital_summary.sql` | Patient-level vital sign summary for clinical review |
| `abnormal_vitals_by_encounter.sql` | Encounter-level abnormal vital sign flags |
| `daily_measurement_counts.sql` | Daily measurement volume by LOINC/OMOP concept |
| `data_quality_exceptions.sql` | Failed DQ checks from the `data_quality_report` table written by the DQ Glue job |
