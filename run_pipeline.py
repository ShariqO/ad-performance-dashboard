#!/usr/bin/env python3
"""
Ad Performance Pipeline — Main Orchestrator
=============================================
Pulls campaign data from Google Ads and Meta Ads (or generates mock data),
runs transformations, and loads everything into BigQuery (or saves locally).

Usage:
    # Full mock mode — no API keys needed, saves to local CSV
    python run_pipeline.py --mock --local

    # Pull real data and load into BigQuery
    python run_pipeline.py

    # Pull real Google data + mock Meta data, save locally
    python run_pipeline.py --mock-meta --local

    # Custom date range (last 7 days)
    python run_pipeline.py --mock --local --days 7

Exit codes:
    0 — Success
    1 — Partial failure (one connector failed, other succeeded)
    2 — Complete failure
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on the path
_project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_project_root))

from config.settings import settings, setup_logging
from connectors.google_ads import GoogleAdsConnector
from connectors.meta_ads import MetaAdsConnector
from pipeline.bigquery_loader import BigQueryLoader
from pipeline.transform import TransformPipeline

import pandas as pd


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Ad Performance Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=settings.app.use_mock_data,
        help="Use mock data for all connectors (default from USE_MOCK_DATA env var)",
    )
    parser.add_argument(
        "--mock-google",
        action="store_true",
        help="Use mock data for Google Ads only",
    )
    parser.add_argument(
        "--mock-meta",
        action="store_true",
        help="Use mock data for Meta Ads only",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        default=settings.app.local_mode,
        help="Save data locally as CSV instead of loading to BigQuery",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=settings.app.lookback_days,
        help=f"Number of days to look back (default: {settings.app.lookback_days})",
    )
    return parser.parse_args()


def main() -> int:
    """
    Run the full ETL pipeline:
        1. Pull data from Google Ads (or mock)
        2. Pull data from Meta Ads (or mock)
        3. Concatenate into a single DataFrame
        4. Run transformations (CPC, CTR, ROAS, trends)
        5. Load into BigQuery (or save as local CSV)
    """
    args = parse_args()
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Ad Performance Pipeline — Starting")
    logger.info("=" * 60)
    logger.info("Mode: %s", "MOCK" if args.mock else "LIVE")
    logger.info("Storage: %s", "LOCAL CSV" if args.local else "BIGQUERY")
    logger.info("Lookback: %d days", args.days)

    # Calculate date range
    from datetime import datetime, timedelta
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    logger.info("Date range: %s → %s", start_date, end_date)

    start_time = time.time()
    all_data: list[pd.DataFrame] = []
    errors: list[str] = []

    # ---- Step 1: Google Ads ----
    logger.info("-" * 40)
    logger.info("Step 1/5: Fetching Google Ads data")
    logger.info("-" * 40)

    google_connector = GoogleAdsConnector()
    use_google_mock = args.mock or args.mock_google

    try:
        if use_google_mock:
            google_df = google_connector.generate_mock_data(start_date, end_date)
        else:
            google_connector.authenticate()
            google_df = google_connector.fetch_campaign_performance(
                start_date, end_date
            )
        logger.info("✅ Google Ads: %d rows", len(google_df))
        all_data.append(google_df)
    except Exception as e:
        logger.error("❌ Google Ads failed: %s", e)
        errors.append(f"Google Ads: {e}")

    # ---- Step 2: Meta Ads ----
    logger.info("-" * 40)
    logger.info("Step 2/5: Fetching Meta Ads data")
    logger.info("-" * 40)

    meta_connector = MetaAdsConnector()
    use_meta_mock = args.mock or args.mock_meta

    try:
        if use_meta_mock:
            meta_df = meta_connector.generate_mock_data(start_date, end_date)
        else:
            meta_connector.authenticate()
            meta_df = meta_connector.fetch_campaign_performance(
                start_date, end_date
            )
        logger.info("✅ Meta Ads: %d rows", len(meta_df))
        all_data.append(meta_df)
    except Exception as e:
        logger.error("❌ Meta Ads failed: %s", e)
        errors.append(f"Meta Ads: {e}")

    # ---- Step 3: Combine ----
    if not all_data:
        logger.error("No data collected from any source. Aborting.")
        return 2

    logger.info("-" * 40)
    logger.info("Step 3/5: Combining data sources")
    logger.info("-" * 40)

    combined_df = pd.concat(all_data, ignore_index=True)
    logger.info("Combined dataset: %d rows", len(combined_df))

    # ---- Step 4: Transform ----
    logger.info("-" * 40)
    logger.info("Step 4/5: Running transformations")
    logger.info("-" * 40)

    transformer = TransformPipeline()
    transformed_df = transformer.run(combined_df)
    logger.info("Transformed dataset: %d rows, %d columns",
                len(transformed_df), len(transformed_df.columns))

    # ---- Step 5: Load ----
    logger.info("-" * 40)
    logger.info("Step 5/5: Loading data")
    logger.info("-" * 40)

    # Override settings with CLI args
    if args.local:
        import os
        os.environ["LOCAL_MODE"] = "true"

    loader = BigQueryLoader()
    loader.initialize()

    rows_loaded = loader.load_data(transformed_df)

    # ---- Summary ----
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Pipeline Complete")
    logger.info("=" * 60)
    logger.info("Rows loaded:  %d", rows_loaded)
    logger.info("Elapsed time: %.1f seconds", elapsed)

    if errors:
        logger.warning("Errors encountered:")
        for err in errors:
            logger.warning("  - %s", err)
        return 1

    logger.info("✅ All steps completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
