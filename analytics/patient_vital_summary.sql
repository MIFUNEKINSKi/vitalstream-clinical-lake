-- Patient-level vital sign summary from curated OMOP measurement data.


SELECT
    p.person_id,
    p.person_source_value AS mrn,
    p.gender_source_value,
    p.year_of_birth,
    m.measurement_concept_id,
    m.measurement_source_value AS loinc_code,
    m.unit_source_value,
    COUNT(*) AS measurement_count,
    MIN(m.measurement_date) AS first_measurement_date,
    MAX(m.measurement_date) AS last_measurement_date,
    ROUND(AVG(m.value_as_number), 2) AS avg_value,
    MIN(m.value_as_number) AS min_value,
    MAX(m.value_as_number) AS max_value
FROM measurement m
JOIN person p
    ON m.person_id = p.person_id
GROUP BY
    p.person_id,
    p.person_source_value,
    p.gender_source_value,
    p.year_of_birth,
    m.measurement_concept_id,
    m.measurement_source_value,
    m.unit_source_value
ORDER BY p.person_id, m.measurement_concept_id;
