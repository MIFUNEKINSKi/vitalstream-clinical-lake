-- Mirrors the pipeline's PCORnet value-set conformance checks
-- (pcornet_data_quality.py run_value_set_checks): coded fields must hold a
-- permissible PCORnet value, defined once in vocabulary.py and delivered via
-- the pcornet_value_sets seed. Rows returned = violations = test failure.

with allowed as (
    select table_name, column_name, allowed_value
    from {{ ref('pcornet_value_sets') }}
),

coded_fields as (
    select 'demographic' as table_name, 'sex' as column_name, patid as row_key, sex as value
    from {{ ref('stg_pcornet__demographic') }}
    union all
    select 'encounter', 'enc_type', encounterid, enc_type
    from {{ ref('stg_pcornet__encounter') }}
    union all
    select 'obs_clin', 'obsclin_type', obsclinid, obsclin_type
    from {{ ref('stg_pcornet__obs_clin') }}
)

select c.table_name, c.column_name, c.row_key, c.value
from coded_fields c
left join allowed a
    on c.table_name = a.table_name
   and c.column_name = a.column_name
   and c.value = a.allowed_value
where a.allowed_value is null
