-- Patient-level vital sign summary for clinical review
-- (dbt port of analytics/patient_vital_summary.sql).

select
    p.person_id,
    p.mrn,
    p.gender_source_value,
    p.year_of_birth,
    d.vital_sign,
    m.measurement_concept_id,
    m.loinc_code,
    m.unit_source_value,
    count(*)                          as measurement_count,
    min(m.measurement_date)           as first_measurement_date,
    max(m.measurement_date)           as last_measurement_date,
    round(avg(m.value_as_number), 2)  as avg_value,
    min(m.value_as_number)            as min_value,
    max(m.value_as_number)            as max_value
from {{ ref('stg_omop__measurement') }} m
join {{ ref('stg_omop__person') }} p
    on m.person_id = p.person_id
left join {{ ref('dim_vital_sign') }} d
    on m.measurement_concept_id = d.measurement_concept_id
group by
    p.person_id,
    p.mrn,
    p.gender_source_value,
    p.year_of_birth,
    d.vital_sign,
    m.measurement_concept_id,
    m.loinc_code,
    m.unit_source_value
