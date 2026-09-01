
  create or replace   view AD_PERFORMANCE.STAGING.stg_google_ads
  
  
  
  
  as (
    -- stg_google_ads.sql
-- Staging model: cleans and standardizes raw Google Ads data
-- Filters to google platform only, casts types, trims strings

with source as (
    select * from AD_PERFORMANCE.RAW.ad_metrics
    where platform = 'google'
),

cleaned as (
    select
        date,
        'google'                        as platform,
        trim(campaign_id)               as campaign_id,
        trim(campaign_name)             as campaign_name,
        coalesce(impressions, 0)        as impressions,
        coalesce(clicks, 0)             as clicks,
        round(coalesce(spend, 0), 2)    as spend,
        round(coalesce(conversions, 0), 2) as conversions,
        round(coalesce(revenue, 0), 2)  as revenue,
        updated_at
    from source
)

select * from cleaned
  );

