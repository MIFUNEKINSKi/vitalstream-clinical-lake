-- Staging: light typing over the curated OMOP measurement table.

select
    cast(measurement_id as bigint)          as measurement_id,
    cast(person_id as bigint)               as person_id,
    cast(measurement_concept_id as integer) as measurement_concept_id,
    cast(measurement_date as date)          as measurement_date,
    cast(measurement_datetime as timestamp) as measurement_datetime,
    cast(measurement_type_concept_id as integer) as measurement_type_concept_id,
    cast(value_as_number as double)         as value_as_number,
    cast(unit_concept_id as integer)        as unit_concept_id,
    unit_source_value,
    measurement_source_value                as loinc_code,
    cast(visit_occurrence_id as bigint)     as visit_occurrence_id
from {{ source('omop', 'measurement') }}
