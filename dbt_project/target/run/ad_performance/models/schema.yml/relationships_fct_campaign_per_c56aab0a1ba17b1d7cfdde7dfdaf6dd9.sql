
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select campaign_id as from_field
    from AD_PERFORMANCE.MARTS.fct_campaign_performance
    where campaign_id is not null
),

parent as (
    select campaign_id as to_field
    from AD_PERFORMANCE.MARTS.dim_campaign
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test