-- Vital-sign dimension: LOINC/OMOP mappings plus DQ and alert thresholds,
-- sourced from the vital_sign_reference seed (generated from vocabulary.py).

select
    cast(omop_concept_id as integer) as measurement_concept_id,
    loinc_code,
    vital_sign,
    abnormal_flag,
    unit_ucum,
    cast(plausible_min as double) as plausible_min,
    cast(plausible_max as double) as plausible_max,
    cast(alert_min as double)     as alert_min,
    cast(alert_max as double)     as alert_max
from {{ ref('vital_sign_reference') }}
