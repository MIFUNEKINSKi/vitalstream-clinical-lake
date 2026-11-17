-- Mirrors the pipeline's OMOP ↔ PCORnet reconciliation checks
-- (pcornet_data_quality.py run_reconciliation_checks): both CDMs come from
-- one FHIR parse, so row counts must agree. Non-BP measurements are one
-- OBS_CLIN row each; a BP measurement is one populated SYSTOLIC/DIASTOLIC
-- value on a VITAL row unless it has no value or a same-code reading shares
-- its patient, encounter and time (VITAL then collapses it, and this test
-- flags the loss). Rows returned = mismatches = test failure.

with counts as (
    select
        'person ↔ DEMOGRAPHIC' as relationship,
        (select count(*) from {{ ref('stg_omop__person') }}) as omop_rows,
        (select count(*) from {{ ref('stg_pcornet__demographic') }}) as pcornet_rows
    union all
    select
        'visit_occurrence ↔ ENCOUNTER',
        (select count(*) from {{ ref('stg_omop__visit_occurrence') }}),
        (select count(*) from {{ ref('stg_pcornet__encounter') }})
    union all
    select
        'measurement ↔ OBS_CLIN + VITAL(SYSTOLIC, DIASTOLIC)',
        (select count(*) from {{ ref('stg_omop__measurement') }}),
        (select count(*) from {{ ref('stg_pcornet__obs_clin') }})
        + (select count(systolic) + count(diastolic) from {{ ref('stg_pcornet__vital') }})
)

select relationship, omop_rows, pcornet_rows
from counts
where omop_rows != pcornet_rows
