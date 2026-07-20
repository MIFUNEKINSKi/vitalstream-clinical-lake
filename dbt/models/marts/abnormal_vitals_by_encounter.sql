-- Encounter-level abnormal vital signs
-- (dbt port of analytics/abnormal_vitals_by_encounter.sql).
-- Alert thresholds come from dim_vital_sign — no hardcoded CASE to keep in
-- sync with vocabulary.py. Flags are dashboard signals, not diagnostic rules.

select
    p.mrn,
    v.visit_occurrence_id,
    v.visit_source_value,
    v.visit_start_datetime,
    m.measurement_datetime,
    m.loinc_code,
    d.vital_sign,
    m.measurement_concept_id,
    m.value_as_number,
    m.unit_source_value,
    d.abnormal_flag
from {{ ref('stg_omop__measurement') }} m
join {{ ref('dim_vital_sign') }} d
    on m.measurement_concept_id = d.measurement_concept_id
join {{ ref('stg_omop__person') }} p
    on m.person_id = p.person_id
left join {{ ref('stg_omop__visit_occurrence') }} v
    on m.visit_occurrence_id = v.visit_occurrence_id
where m.value_as_number < d.alert_min
   or m.value_as_number > d.alert_max
