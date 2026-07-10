"""
Transformation Pipeline
========================
Calculates derived metrics from raw ad performance data:
    - Cost per click (CPC)
    - Click-through rate (CTR)
    - Cost per conversion
    - Return on ad spend (ROAS)
    - Daily trends (day-over-day changes, 7-day moving averages)
    - Platform-level aggregations

All transformations handle division-by-zero edge cases gracefully.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger("ad_dashboard.transform")


class TransformPipeline:
    """Computes derived metrics and trend analysis on ad performance data."""

    # ------------------------------------------------------------------
    # Core derived metrics
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add calculated columns to the DataFrame:
            - cost_per_click      = spend / clicks
            - click_through_rate  = (clicks / impressions) * 100
            - cost_per_conversion = spend / conversions
            - roas                = revenue / spend

        All divisions are safe (NaN when denominator is 0, then filled to 0).
        """
        if df.empty:
            logger.warning("Empty DataFrame passed to calculate_derived_metrics")
            return df

        df = df.copy()

        # Cost per click
        df["cost_per_click"] = (
            df["spend"]
            .div(df["clicks"].replace(0, float("nan")))
            .round(2)
            .fillna(0)
        )

        # Click-through rate (as a percentage)
        df["click_through_rate"] = (
            df["clicks"]
            .div(df["impressions"].replace(0, float("nan")))
            .mul(100)
            .round(2)
            .fillna(0)
        )

        # Cost per conversion
        df["cost_per_conversion"] = (
            df["spend"]
            .div(df["conversions"].replace(0, float("nan")))
            .round(2)
            .fillna(0)
        )

        # Return on ad spend
        df["roas"] = (
            df["revenue"]
            .div(df["spend"].replace(0, float("nan")))
            .round(2)
            .fillna(0)
        )

        logger.info("Calculated derived metrics for %d rows", len(df))
        return df

    # ------------------------------------------------------------------
    # Daily trends
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_daily_trends(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add trend columns for key metrics:
            - spend_7d_ma:     7-day moving average of spend
            - clicks_7d_ma:    7-day moving average of clicks
            - ctr_7d_ma:       7-day moving average of CTR
            - spend_pct_change: day-over-day percentage change in spend

        Trends are calculated per campaign to avoid cross-campaign smoothing.
        """
        if df.empty:
            return df

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["platform", "campaign_id", "date"])

        # Group by campaign for per-campaign trends
        grouped = df.groupby(["platform", "campaign_id"])

        df["spend_7d_ma"] = (
            grouped["spend"]
            .transform(lambda x: x.rolling(window=7, min_periods=1).mean())
            .round(2)
        )

        df["clicks_7d_ma"] = (
            grouped["clicks"]
            .transform(lambda x: x.rolling(window=7, min_periods=1).mean())
            .round(1)
        )

        # CTR moving average needs to be computed from the ratio, not averaged
        if "click_through_rate" in df.columns:
            df["ctr_7d_ma"] = (
                grouped["click_through_rate"]
                .transform(lambda x: x.rolling(window=7, min_periods=1).mean())
                .round(2)
            )

        # Day-over-day spend change (percentage)
        df["spend_pct_change"] = (
            grouped["spend"]
            .transform(lambda x: x.pct_change())
            .mul(100)
            .round(1)
            .fillna(0)
        )

        logger.info("Calculated daily trends for %d rows", len(df))
        return df

    # ------------------------------------------------------------------
    # Aggregations
    # ------------------------------------------------------------------

    @staticmethod
    def aggregate_by_platform(df: pd.DataFrame) -> pd.DataFrame:
        """
        Roll up metrics to the platform level across all campaigns.

        Returns one row per platform per date with summed metrics
        and recalculated ratios.
        """
        if df.empty:
            return df

        agg_df = (
            df.groupby(["date", "platform"])
            .agg({
                "impressions": "sum",
                "clicks": "sum",
                "spend": "sum",
                "conversions": "sum",
                "revenue": "sum",
            })
            .reset_index()
        )

        # Recalculate ratios on the aggregated numbers
        pipeline = TransformPipeline()
        agg_df = pipeline.calculate_derived_metrics(agg_df)

        logger.info(
            "Aggregated to %d platform-level rows", len(agg_df)
        )
        return agg_df

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the full transformation pipeline:
            1. Calculate derived metrics (CPC, CTR, cost/conv, ROAS)
            2. Calculate daily trends (7d MA, DoD changes)

        Args:
            df: Raw ad performance DataFrame with columns:
                date, platform, campaign_id, campaign_name,
                impressions, clicks, spend, conversions, revenue

        Returns:
            Enriched DataFrame with all derived and trend columns added.
        """
        logger.info("Running transformation pipeline on %d rows", len(df))

        df = self.calculate_derived_metrics(df)
        df = self.calculate_daily_trends(df)

        logger.info("Transformation pipeline complete — %d rows, %d columns",
                     len(df), len(df.columns))
        return df
