-- Staging: light typing and renames over the curated OMOP person table.

select
    cast(person_id as bigint)            as person_id,
    cast(gender_concept_id as integer)   as gender_concept_id,
    cast(year_of_birth as integer)       as year_of_birth,
    cast(month_of_birth as integer)      as month_of_birth,
    cast(day_of_birth as integer)        as day_of_birth,
    cast(birth_datetime as timestamp)    as birth_datetime,
    cast(race_concept_id as integer)     as race_concept_id,
    cast(ethnicity_concept_id as integer) as ethnicity_concept_id,
    person_source_value                  as mrn,
    gender_source_value
from {{ source('omop', 'person') }}
