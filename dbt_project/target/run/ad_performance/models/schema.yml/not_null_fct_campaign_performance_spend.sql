
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select spend
from AD_PERFORMANCE.MARTS.fct_campaign_performance
where spend is null



  
  
      
    ) dbt_internal_test