-- Staging: light typing over the PCORnet ENCOUNTER table.

select
    cast(ENCOUNTERID as varchar)    as encounterid,
    cast(PATID as varchar)          as patid,
    cast(ADMIT_DATE as date)        as admit_date,
    cast(ADMIT_TIME as varchar)     as admit_time,
    cast(DISCHARGE_DATE as date)    as discharge_date,
    cast(DISCHARGE_TIME as varchar) as discharge_time,
    cast(ENC_TYPE as varchar)       as enc_type,
    cast(RAW_ENC_TYPE as varchar)   as raw_enc_type
from {{ source('pcornet', 'encounter') }}
