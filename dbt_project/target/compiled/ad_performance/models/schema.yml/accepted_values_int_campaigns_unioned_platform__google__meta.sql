
    
    

with all_values as (

    select
        platform as value_field,
        count(*) as n_records

    from AD_PERFORMANCE.INTERMEDIATE.int_campaigns_unioned
    group by platform

)

select *
from all_values
where value_field not in (
    'google','meta'
)


