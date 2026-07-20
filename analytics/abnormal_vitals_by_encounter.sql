-- Encounter-level abnormal vital signs based on clinically plausible alert thresholds.
-- These thresholds are intentionally simple dashboard flags, not diagnostic rules.
-- concept_ids must stay in sync with src/data_generator/vocabulary.py VITAL_SIGNS,
-- the single source of truth for the vital signs this pipeline maps.

WITH flagged_measurements AS (
    SELECT
        m.person_id,
        m.visit_occurrence_id,
        m.measurement_datetime,
        m.measurement_concept_id,
        m.measurement_source_value AS loinc_code,
        m.value_as_number,
        m.unit_source_value,
        CASE
            WHEN m.measurement_concept_id = 3027018
                AND (m.value_as_number < 50 OR m.value_as_number > 120)
                THEN 'abnormal_heart_rate'
            WHEN m.measurement_concept_id = 3004249
                AND (m.value_as_number < 90 OR m.value_as_number > 140)
                THEN 'abnormal_systolic_bp'
            WHEN m.measurement_concept_id = 3012888
                AND (m.value_as_number < 60 OR m.value_as_number > 90)
                THEN 'abnormal_diastolic_bp'
            WHEN m.measurement_concept_id = 3020891
                AND (m.value_as_number < 36 OR m.value_as_number > 38)
                THEN 'abnormal_temperature'
            WHEN m.measurement_concept_id = 3024171
                AND (m.value_as_number < 12 OR m.value_as_number > 24)
                THEN 'abnormal_respiratory_rate'
            WHEN m.measurement_concept_id = 3016502
                AND m.value_as_number < 95
                THEN 'low_oxygen_saturation'
        END AS abnormal_flag
    FROM measurement m
)

SELECT
    p.person_source_value AS mrn,
    v.visit_occurrence_id,
    v.visit_source_value,
    v.visit_start_datetime,
    f.measurement_datetime,
    f.loinc_code,
    f.measurement_concept_id,
    f.value_as_number,
    f.unit_source_value,
    f.abnormal_flag
FROM flagged_measurements f
JOIN person p
    ON f.person_id = p.person_id
LEFT JOIN visit_occurrence v
    ON f.visit_occurrence_id = v.visit_occurrence_id
WHERE f.abnormal_flag IS NOT NULL
ORDER BY v.visit_start_datetime DESC, f.measurement_datetime DESC;
