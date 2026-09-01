-- stg_meta_ads.sql
-- Staging model: cleans and standardizes raw Meta Ads data
-- Filters to meta platform only, casts types, trims strings

with source as (
    select * from {{ source('raw', 'ad_metrics') }}
    where platform = 'meta'
),

cleaned as (
    select
        date,
        'meta'                          as platform,
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
