
  create or replace   view AD_PERFORMANCE.INTERMEDIATE.int_campaigns_unioned
  
  
  
  
  as (
    -- int_campaigns_unioned.sql
-- Intermediate model: unions Google and Meta staging models
-- into a single normalized structure for downstream consumption

with google as (
    select * from AD_PERFORMANCE.STAGING.stg_google_ads
),

meta as (
    select * from AD_PERFORMANCE.STAGING.stg_meta_ads
),

unioned as (
    select * from google
    union all
    select * from meta
)

select * from unioned
  );

