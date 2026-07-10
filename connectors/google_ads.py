"""
Google Ads API Connector
========================
Pulls campaign-level performance data from the Google Ads API using GAQL
(Google Ads Query Language).  Falls back to realistic mock data when
credentials are unavailable or --mock mode is enabled.

The connector returns a normalized pandas DataFrame that matches the common
schema used by the BigQuery loader.

Authentication requires:
    - Developer token (from your Google Ads Manager account)
    - OAuth2 client ID + secret (from GCP Console)
    - Refresh token (generated via the google-ads OAuth flow)
    - Customer ID (the ad account to query)
    - Login customer ID (your MCC / manager account ID)
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from config.settings import settings

logger = logging.getLogger("ad_dashboard.google_ads")


# ---------------------------------------------------------------------------
# GAQL query template
# ---------------------------------------------------------------------------

_CAMPAIGN_PERFORMANCE_QUERY = """
    SELECT
        segments.date,
        campaign.id,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
    FROM campaign
    WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
      AND campaign.status = 'ENABLED'
    ORDER BY segments.date DESC
"""


class GoogleAdsConnector:
    """Fetches campaign performance data from the Google Ads API."""

    PLATFORM = "google"

    def __init__(self) -> None:
        self._client = None
        self._config = settings.google_ads

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """
        Initialize the GoogleAdsClient from environment-based credentials.

        Uses the google-ads library's dict-based configuration so we don't
        need a google-ads.yaml file — everything comes from env vars.
        """
        if not self._config.is_configured:
            logger.warning(
                "Google Ads credentials not configured — "
                "use --mock flag or set environment variables"
            )
            return

        try:
            from google.ads.googleads.client import GoogleAdsClient

            credentials = {
                "developer_token": self._config.developer_token,
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "refresh_token": self._config.refresh_token,
                "login_customer_id": self._config.login_customer_id,
                "use_proto_plus": True,
            }
            self._client = GoogleAdsClient.load_from_dict(credentials)
            logger.info("Google Ads client authenticated successfully")
        except Exception as e:
            logger.error("Failed to authenticate with Google Ads API: %s", e)
            raise

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def fetch_campaign_performance(
        self, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Pull campaign performance metrics for the given date range.

        Args:
            start_date: YYYY-MM-DD format
            end_date:   YYYY-MM-DD format

        Returns:
            DataFrame with columns matching the common ad_performance schema.
        """
        if self._client is None:
            raise RuntimeError(
                "Client not authenticated. Call authenticate() first, "
                "or use generate_mock_data() for demo mode."
            )

        logger.info(
            "Fetching Google Ads data: %s → %s for customer %s",
            start_date, end_date, self._config.customer_id,
        )

        query = self._build_query(start_date, end_date)
        ga_service = self._client.get_service("GoogleAdsService")

        try:
            response = ga_service.search_stream(
                customer_id=self._config.customer_id,
                query=query,
            )
            rows = self._parse_response(response)
            logger.info("Fetched %d rows from Google Ads", len(rows))
        except Exception as e:
            logger.error("Google Ads API request failed: %s", e)
            raise

        if not rows:
            logger.warning("No campaign data returned for the date range")
            return self._empty_dataframe()

        df = pd.DataFrame(rows)
        return df

    # ------------------------------------------------------------------
    # Query construction
    # ------------------------------------------------------------------

    def _build_query(self, start_date: str, end_date: str) -> str:
        """Build a GAQL query string with the date range substituted in."""
        return _CAMPAIGN_PERFORMANCE_QUERY.format(
            start_date=start_date, end_date=end_date
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, response_stream: Any) -> list[dict]:
        """
        Convert the streaming API response into a flat list of dicts.

        Google Ads returns costs in micros (1/1,000,000 of a currency unit),
        so we divide by 1_000_000 to get actual dollar amounts.
        """
        rows: list[dict] = []

        for batch in response_stream:
            for row in batch.results:
                rows.append({
                    "date": row.segments.date,
                    "platform": self.PLATFORM,
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": row.campaign.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "spend": row.metrics.cost_micros / 1_000_000,
                    "conversions": row.metrics.conversions,
                    "revenue": row.metrics.conversions_value,
                })

        return rows

    # ------------------------------------------------------------------
    # Mock data generator
    # ------------------------------------------------------------------

    def generate_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Generate realistic-looking fake Google Ads campaign data.

        Useful for:
            - Demos without API credentials
            - Testing the pipeline end-to-end
            - Showcasing the dashboard at interviews

        The mock data simulates 4 campaigns with varying performance
        characteristics and realistic daily fluctuations.
        """
        logger.info("Generating mock Google Ads data: %s → %s", start_date, end_date)

        campaigns = [
            {"id": "100001", "name": "Brand Awareness - Search",
             "base_impressions": 12000, "base_ctr": 0.035, "base_cpc": 1.20, "conv_rate": 0.04},
            {"id": "100002", "name": "Product Launch - Display",
             "base_impressions": 45000, "base_ctr": 0.008, "base_cpc": 0.45, "conv_rate": 0.01},
            {"id": "100003", "name": "Retargeting - Shopping",
             "base_impressions": 8000, "base_ctr": 0.052, "base_cpc": 0.85, "conv_rate": 0.08},
            {"id": "100004", "name": "Lead Gen - Search",
             "base_impressions": 6000, "base_ctr": 0.042, "base_cpc": 2.10, "conv_rate": 0.06},
        ]

        rows: list[dict] = []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        current = start

        random.seed(42)  # Reproducible data

        while current <= end:
            # Weekend dip factor
            day_factor = 0.7 if current.weekday() >= 5 else 1.0

            for camp in campaigns:
                impressions = int(
                    camp["base_impressions"] * day_factor * random.uniform(0.8, 1.2)
                )
                clicks = int(impressions * camp["base_ctr"] * random.uniform(0.85, 1.15))
                spend = round(clicks * camp["base_cpc"] * random.uniform(0.9, 1.1), 2)
                conversions = round(
                    clicks * camp["conv_rate"] * random.uniform(0.7, 1.3), 1
                )
                # Simulate revenue: average order value ~$50-150
                revenue = round(conversions * random.uniform(50, 150), 2)

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
        logger.info("Generated %d mock Google Ads rows", len(df))
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
