"""
Meta (Facebook) Ads API Connector
===================================
Pulls campaign-level performance data from the Meta Marketing API using
the facebook-business Python SDK.  Falls back to realistic mock data
when credentials are unavailable or --mock mode is enabled.

The connector returns a normalized pandas DataFrame that matches the common
schema used by the BigQuery loader, identical in structure to the Google
Ads connector output.

Authentication requires:
    - Facebook App ID and App Secret (from developers.facebook.com)
    - Long-lived access token (generated via the App dashboard or token tool)
    - Ad Account ID in the format act_XXXXXXXXXX
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from config.settings import settings

logger = logging.getLogger("ad_dashboard.meta_ads")


class MetaAdsConnector:
    """Fetches campaign performance data from the Meta Marketing API."""

    PLATFORM = "meta"

    def __init__(self) -> None:
        self._api = None
        self._ad_account = None
        self._config = settings.meta_ads

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """
        Initialize the Facebook Ads API client and resolve the ad account.

        Uses the facebook-business SDK's initialization pattern:
        FacebookAdsApi.init() sets a global default session.
        """
        if not self._config.is_configured:
            logger.warning(
                "Meta Ads credentials not configured — "
                "use --mock flag or set environment variables"
            )
            return

        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount

            self._api = FacebookAdsApi.init(
                app_id=self._config.app_id,
                app_secret=self._config.app_secret,
                access_token=self._config.access_token,
            )

            self._ad_account = AdAccount(self._config.ad_account_id)
            logger.info(
                "Meta Ads client authenticated for account %s",
                self._config.ad_account_id,
            )
        except Exception as e:
            logger.error("Failed to authenticate with Meta Ads API: %s", e)
            raise

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def fetch_campaign_performance(
        self, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Pull campaign performance metrics for the given date range.

        Uses the Ad Account Insights endpoint with campaign-level breakdown.
        Handles pagination automatically via the SDK's cursor.

        Args:
            start_date: YYYY-MM-DD format
            end_date:   YYYY-MM-DD format

        Returns:
            DataFrame with columns matching the common ad_performance schema.
        """
        if self._ad_account is None:
            raise RuntimeError(
                "Client not authenticated. Call authenticate() first, "
                "or use generate_mock_data() for demo mode."
            )

        logger.info(
            "Fetching Meta Ads data: %s → %s for account %s",
            start_date, end_date, self._config.ad_account_id,
        )

        params = {
            "time_range": {
                "since": start_date,
                "until": end_date,
            },
            "time_increment": 1,  # Daily breakdown
            "level": "campaign",
            "filtering": [
                {
                    "field": "campaign.effective_status",
                    "operator": "IN",
                    "value": ["ACTIVE", "PAUSED"],
                }
            ],
        }

        fields = [
            "campaign_id",
            "campaign_name",
            "date_start",
            "impressions",
            "clicks",
            "spend",
            "actions",           # Contains conversion events
            "action_values",     # Contains conversion values (revenue)
        ]

        try:
            insights = self._ad_account.get_insights(
                params=params,
                fields=fields,
            )
            rows = self._parse_insights(insights)
            logger.info("Fetched %d rows from Meta Ads", len(rows))
        except Exception as e:
            logger.error("Meta Ads API request failed: %s", e)
            raise

        if not rows:
            logger.warning("No campaign data returned for the date range")
            return self._empty_dataframe()

        df = pd.DataFrame(rows)
        return df

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_insights(self, insights: Any) -> list[dict]:
        """
        Convert the Insights API response into a flat list of dicts.

        Meta's API returns conversions inside an 'actions' array where each
        element has an 'action_type' and 'value'.  We extract 'purchase' and
        'lead' actions as our conversion count.  Revenue comes from
        'action_values' with type 'offsite_conversion.fb_pixel_purchase'.
        """
        rows: list[dict] = []

        for insight in insights:
            # Extract conversions from the actions array
            conversions = 0.0
            actions = insight.get("actions") or []
            for action in actions:
                if action["action_type"] in (
                    "purchase",
                    "lead",
                    "offsite_conversion.fb_pixel_purchase",
                    "offsite_conversion.fb_pixel_lead",
                ):
                    conversions += float(action["value"])

            # Extract revenue from action_values
            revenue = 0.0
            action_values = insight.get("action_values") or []
            for av in action_values:
                if av["action_type"] in (
                    "offsite_conversion.fb_pixel_purchase",
                    "purchase",
                ):
                    revenue += float(av["value"])

            rows.append({
                "date": insight["date_start"],
                "platform": self.PLATFORM,
                "campaign_id": insight["campaign_id"],
                "campaign_name": insight["campaign_name"],
                "impressions": int(insight.get("impressions", 0)),
                "clicks": int(insight.get("clicks", 0)),
                "spend": float(insight.get("spend", 0)),
                "conversions": conversions,
                "revenue": revenue,
            })

        return rows

    # ------------------------------------------------------------------
    # Mock data generator
    # ------------------------------------------------------------------

    def generate_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Generate realistic-looking fake Meta Ads campaign data.

        Simulates 3 Meta campaigns with characteristics typical of Facebook
        and Instagram ad delivery (higher impressions, lower CPC than Google,
        different conversion patterns).
        """
        logger.info("Generating mock Meta Ads data: %s → %s", start_date, end_date)

        campaigns = [
            {"id": "200001", "name": "Summer Sale - Feed",
             "base_impressions": 55000, "base_ctr": 0.012, "base_cpc": 0.35, "conv_rate": 0.02},
            {"id": "200002", "name": "App Install - Stories",
             "base_impressions": 80000, "base_ctr": 0.006, "base_cpc": 0.22, "conv_rate": 0.005},
            {"id": "200003", "name": "Retargeting - Carousel",
             "base_impressions": 15000, "base_ctr": 0.025, "base_cpc": 0.55, "conv_rate": 0.045},
        ]

        rows: list[dict] = []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        current = start

        random.seed(99)  # Different seed from Google for variety

        while current <= end:
            # Meta campaigns often see slight weekend boosts (social usage)
            day_factor = 1.15 if current.weekday() >= 5 else 1.0

            for camp in campaigns:
                impressions = int(
                    camp["base_impressions"] * day_factor * random.uniform(0.8, 1.2)
                )
                clicks = int(impressions * camp["base_ctr"] * random.uniform(0.85, 1.15))
                spend = round(clicks * camp["base_cpc"] * random.uniform(0.9, 1.1), 2)
                conversions = round(
                    clicks * camp["conv_rate"] * random.uniform(0.7, 1.3), 1
                )
                revenue = round(conversions * random.uniform(30, 120), 2)

                rows.append({
                    "date": current.strftime("%Y-%m-%d"),
                    "platform": self.PLATFORM,
                    "campaign_id": camp["id"],
                    "campaign_name": camp["name"],
                    "impressions": impressions,
                    "clicks": max(clicks, 0),
                    "spend": max(spend, 0),
                    "conversions": max(conversions, 0),
                    "revenue": max(revenue, 0),
                })

            current += timedelta(days=1)

        df = pd.DataFrame(rows)
        logger.info("Generated %d mock Meta Ads rows", len(df))
        return df

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_dataframe() -> pd.DataFrame:
        """Return an empty DataFrame with the expected columns."""
        return pd.DataFrame(columns=[
            "date", "platform", "campaign_id", "campaign_name",
            "impressions", "clicks", "spend", "conversions", "revenue",
        ])
