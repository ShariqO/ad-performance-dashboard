
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select platform
from AD_PERFORMANCE.INTERMEDIATE.int_campaigns_unioned
where platform is null



  
  
      
    ) dbt_internal_test