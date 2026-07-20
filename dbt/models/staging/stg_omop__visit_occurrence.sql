-- Staging: light typing over the curated OMOP visit_occurrence table.

select
    cast(visit_occurrence_id as bigint)  as visit_occurrence_id,
    cast(person_id as bigint)            as person_id,
    cast(visit_concept_id as integer)    as visit_concept_id,
    cast(visit_start_date as date)       as visit_start_date,
    cast(visit_start_datetime as timestamp) as visit_start_datetime,
    cast(visit_end_date as date)         as visit_end_date,
    cast(visit_end_datetime as timestamp) as visit_end_datetime,
    cast(visit_type_concept_id as integer) as visit_type_concept_id,
    visit_source_value
from {{ source('omop', 'visit_occurrence') }}
