-- Staging: light typing over the PCORnet OBS_CLIN table.

select
    cast(OBSCLINID as varchar)             as obsclinid,
    cast(PATID as varchar)                 as patid,
    cast(ENCOUNTERID as varchar)           as encounterid,
    cast(OBSCLIN_START_DATE as date)       as obsclin_start_date,
    cast(OBSCLIN_START_TIME as varchar)    as obsclin_start_time,
    cast(OBSCLIN_TYPE as varchar)          as obsclin_type,
    cast(OBSCLIN_CODE as varchar)          as obsclin_code,
    cast(OBSCLIN_RESULT_NUM as double)     as obsclin_result_num,
    cast(OBSCLIN_RESULT_UNIT as varchar)   as obsclin_result_unit,
    cast(OBSCLIN_SOURCE as varchar)        as obsclin_source
from {{ source('pcornet', 'obs_clin') }}
