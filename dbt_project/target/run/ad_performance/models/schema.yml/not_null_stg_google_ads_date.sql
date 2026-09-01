
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select date
from AD_PERFORMANCE.STAGING.stg_google_ads
where date is null



  
  
      
    ) dbt_internal_test