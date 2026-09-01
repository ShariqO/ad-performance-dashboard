-- fct_daily_platform_summary.sql
-- Fact table: aggregated daily performance metrics per platform
-- Powers the dashboard's platform-level trend charts and KPI cards

with campaign_performance as (
    select * from {{ ref('fct_campaign_performance') }}
),

daily_summary as (
    select
        date,
        platform,
        count(distinct campaign_id)     as active_campaigns,
        sum(impressions)                as total_impressions,
        sum(clicks)                     as total_clicks,
        round(sum(spend), 2)            as total_spend,
        round(sum(conversions), 2)      as total_conversions,
        round(sum(revenue), 2)          as total_revenue,

        -- Platform-level derived metrics
        case
            when sum(clicks) > 0 then round(sum(spend) / sum(clicks), 4)
            else 0
        end as avg_cpc,

        case
            when sum(impressions) > 0 then round((sum(clicks) / sum(impressions)) * 100, 4)
            else 0
        end as avg_ctr,

        case
            when sum(spend) > 0 then round(sum(revenue) / sum(spend), 4)
            else 0
        end as avg_roas
    from campaign_performance
    group by date, platform
)

select * from daily_summary
