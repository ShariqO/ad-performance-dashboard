
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_spend
from AD_PERFORMANCE.MARTS.fct_daily_platform_summary
where total_spend is null



  
  
      
    ) dbt_internal_test