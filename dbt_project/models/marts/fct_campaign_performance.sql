-- fct_campaign_performance.sql
-- Fact table: daily campaign performance with derived metrics
-- Replaces the old Python transform pipeline (CPC, CTR, ROAS, etc.)

with base as (
    select * from {{ ref('int_campaigns_unioned') }}
),

with_metrics as (
    select
        date,
        platform,
        campaign_id,
        campaign_name,
        impressions,
        clicks,
        spend,
        conversions,
        revenue,

        -- Derived metrics (replacing pipeline/transform.py)
        case
            when clicks > 0 then round(spend / clicks, 4)
            else 0
        end as cost_per_click,

        case
            when impressions > 0 then round((clicks / impressions) * 100, 4)
            else 0
        end as click_through_rate,

        case
            when conversions > 0 then round(spend / conversions, 4)
            else 0
        end as cost_per_conversion,

        case
            when spend > 0 then round(revenue / spend, 4)
            else 0
        end as roas,

        updated_at
    from base
)

select * from with_metrics
