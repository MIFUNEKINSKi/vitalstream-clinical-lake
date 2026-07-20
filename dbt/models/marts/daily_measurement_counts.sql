-- Daily measurement volume by OMOP concept and source LOINC code
-- (dbt port of analytics/daily_measurement_counts.sql).

select
    m.measurement_date,
    m.measurement_concept_id,
    m.loinc_code,
    d.vital_sign,
    count(*)                                as measurement_count,
    count(distinct m.person_id)             as patient_count,
    count(distinct m.visit_occurrence_id)   as encounter_count
from {{ ref('stg_omop__measurement') }} m
left join {{ ref('dim_vital_sign') }} d
    on m.measurement_concept_id = d.measurement_concept_id
group by
    m.measurement_date,
    m.measurement_concept_id,
    m.loinc_code,
    d.vital_sign
