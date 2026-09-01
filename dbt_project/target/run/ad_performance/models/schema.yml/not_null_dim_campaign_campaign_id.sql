
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select campaign_id
from AD_PERFORMANCE.MARTS.dim_campaign
where campaign_id is null



  
  
      
    ) dbt_internal_test