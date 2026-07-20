-- Mirrors the pipeline's PySpark range checks (data_quality.py
-- run_range_checks): every vital-sign measurement must fall inside the
-- clinically plausible range defined in vocabulary.py (via dim_vital_sign).
-- Rows returned = violations = test failure.

select
    m.measurement_id,
    m.measurement_concept_id,
    d.vital_sign,
    m.value_as_number,
    d.plausible_min,
    d.plausible_max
from {{ ref('stg_omop__measurement') }} m
join {{ ref('dim_vital_sign') }} d
    on m.measurement_concept_id = d.measurement_concept_id
where m.value_as_number < d.plausible_min
   or m.value_as_number > d.plausible_max
