"""
Dagster Software-Defined Assets
================================
Defines the end-to-end data pipeline asset graph:
  1. Extract Google Ads performance data -> raw_google_ads_data
  2. Extract Meta Ads performance data   -> raw_meta_ads_data
  3. Load raw data into Snowflake via MERGE -> snowflake_raw_ad_metrics
  4. Run dbt models (Staging -> Intermediate -> Marts) via dagster-dbt
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dagster import AssetExecutionContext, AssetIn, AssetKey, OpExecutionContext, RetryPolicy, asset
from dagster_dbt import DbtCliResource, dbt_assets

from connectors.google_ads import GoogleAdsConnector
from connectors.meta_ads import MetaAdsConnector
from loader.snowflake_loader import SnowflakeLoader

# Locate dbt manifest
DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent / "dbt_project"
MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"

# Retry policy for extract/load assets (up to 3 retries with 10s backoff)
DEFAULT_RETRY_POLICY = RetryPolicy(max_retries=3, delay=10)


@asset(
    group_name="ingestion",
    description="Extract campaign performance metrics from Google Ads API (or mock generator)",
    retry_policy=DEFAULT_RETRY_POLICY,
)
def raw_google_ads_data(context: AssetExecutionContext) -> pd.DataFrame:
    """Extract raw Google Ads performance data."""
    lookback = int(os.getenv("LOOKBACK_DAYS", "30"))
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

    context.log.info(f"Extracting Google Ads data from {start_date} to {end_date}")

    connector = GoogleAdsConnector()
    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1")

    if use_mock:
        df = connector.generate_mock_data(start_date, end_date)
    else:
        connector.authenticate()
        df = connector.fetch_campaign_performance(start_date, end_date)

    context.log.info(f"Extracted {len(df)} rows from Google Ads")
    return df


@asset(
    group_name="ingestion",
    description="Extract campaign performance metrics from Meta Ads API (or mock generator)",
    retry_policy=DEFAULT_RETRY_POLICY,
)
def raw_meta_ads_data(context: AssetExecutionContext) -> pd.DataFrame:
    """Extract raw Meta Ads performance data."""
    lookback = int(os.getenv("LOOKBACK_DAYS", "30"))
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

    context.log.info(f"Extracting Meta Ads data from {start_date} to {end_date}")

    connector = MetaAdsConnector()
    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1")

    if use_mock:
        df = connector.generate_mock_data(start_date, end_date)
    else:
        connector.authenticate()
        df = connector.fetch_campaign_performance(start_date, end_date)

    context.log.info(f"Extracted {len(df)} rows from Meta Ads")
    return df


@asset(
    group_name="storage",
    description="Load raw ad metrics into Snowflake AD_PERFORMANCE.RAW.AD_METRICS via MERGE upsert",
    ins={
        "google_data": AssetIn("raw_google_ads_data"),
        "meta_data": AssetIn("raw_meta_ads_data"),
    },
    retry_policy=DEFAULT_RETRY_POLICY,
)
def snowflake_raw_ad_metrics(
    context: AssetExecutionContext, google_data: pd.DataFrame, meta_data: pd.DataFrame
) -> int:
    """Combine ad platform extracts and load into Snowflake RAW schema."""
    frames = [df for df in [google_data, meta_data] if not df.empty]
    if not frames:
        context.log.warning("No data returned from connectors — skipping load")
        return 0

    combined_df = pd.concat(frames, ignore_index=True)
    context.log.info(f"Combined extract total rows: {len(combined_df)}")

    loader = SnowflakeLoader()
    loader.initialize()
    rows_affected = loader.load_data(combined_df)
    loader.close()

    context.log.info(f"Successfully MERGED {rows_affected} rows into Snowflake RAW.AD_METRICS")
    return rows_affected


@dbt_assets(
    manifest=MANIFEST_PATH,
    name="dbt_ad_performance",
)
def dbt_ad_performance_assets(context: OpExecutionContext, dbt: DbtCliResource):
    """Execute dbt models (Staging -> Intermediate -> Marts) and tests."""
    yield from dbt.cli(["build"], context=context).stream()
