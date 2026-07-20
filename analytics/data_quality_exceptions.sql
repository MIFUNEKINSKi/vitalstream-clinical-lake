-- Failed data-quality checks for dashboarding.
-- The data_quality_report table is written one row per check by the DQ Glue job
-- (src/glue_jobs/data_quality.py, DQ_REPORT_ROW_SCHEMA) to
-- {dq_output_path}/data_quality_report/ and registered by the Glue crawler.
-- Fields not applicable to a check type are null, hence the COALESCEs.

SELECT
    run_timestamp,
    check_type,
    COALESCE("table", measurement, relationship) AS check_subject,
    "column" AS check_column,
    total_rows,
    COALESCE(violations, orphan_count, 0) AS exception_count,
    passed
FROM data_quality_report
WHERE passed = false
ORDER BY run_timestamp DESC, exception_count DESC;
