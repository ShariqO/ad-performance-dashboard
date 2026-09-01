
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select campaign_id
from AD_PERFORMANCE.INTERMEDIATE.int_campaigns_unioned
where campaign_id is null



  
  
      
    ) dbt_internal_test