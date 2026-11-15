-- Staging: light typing over the PCORnet VITAL table.

select
    cast(VITALID as varchar)      as vitalid,
    cast(PATID as varchar)        as patid,
    cast(ENCOUNTERID as varchar)  as encounterid,
    cast(MEASURE_DATE as date)    as measure_date,
    cast(MEASURE_TIME as varchar) as measure_time,
    cast(VITAL_SOURCE as varchar) as vital_source,
    cast(SYSTOLIC as double)      as systolic,
    cast(DIASTOLIC as double)     as diastolic,
    cast(BP_POSITION as varchar)  as bp_position
from {{ source('pcornet', 'vital') }}
