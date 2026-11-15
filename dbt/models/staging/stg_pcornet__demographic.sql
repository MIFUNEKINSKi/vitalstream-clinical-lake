-- Staging: light typing over the PCORnet DEMOGRAPHIC table
-- (lower-cased column names for warehouse ergonomics).

select
    cast(PATID as varchar)      as patid,
    cast(BIRTH_DATE as date)    as birth_date,
    cast(BIRTH_TIME as varchar) as birth_time,
    cast(SEX as varchar)        as sex,
    cast(HISPANIC as varchar)   as hispanic,
    cast(RACE as varchar)       as race,
    cast(RAW_SEX as varchar)    as raw_sex
from {{ source('pcornet', 'demographic') }}
