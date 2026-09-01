-- dim_campaign.sql
-- Dimension table: one row per unique campaign
-- Provides a lookup of campaign attributes

with campaigns as (
    select
        campaign_id,
        campaign_name,
        platform,
        min(date)           as first_seen_date,
        max(date)           as last_seen_date,
        count(distinct date) as active_days
    from AD_PERFORMANCE.INTERMEDIATE.int_campaigns_unioned
    group by campaign_id, campaign_name, platform
)

select * from campaigns