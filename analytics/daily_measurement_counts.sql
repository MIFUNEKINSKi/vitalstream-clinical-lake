-- Daily measurement volume by OMOP concept and source LOINC code.

SELECT
    m.measurement_date,
    m.measurement_concept_id,
    m.measurement_source_value AS loinc_code,
    COUNT(*) AS measurement_count,
    COUNT(DISTINCT m.person_id) AS patient_count,
    COUNT(DISTINCT m.visit_occurrence_id) AS encounter_count
FROM measurement m
GROUP BY
    m.measurement_date,
    m.measurement_concept_id,
    m.measurement_source_value
ORDER BY m.measurement_date DESC, m.measurement_concept_id;
