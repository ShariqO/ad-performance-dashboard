"""
BigQuery Loader
===============
Handles creating the dataset/table in BigQuery and loading DataFrames
into the ad_performance table.  Uses WRITE_TRUNCATE to keep storage
minimal on the free tier — each run replaces data for the date range.

Also provides a read method so the Streamlit dashboard can query
BigQuery directly.

In local mode, falls back to reading/writing CSV files in the data/ dir.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import settings

logger = logging.getLogger("ad_dashboard.bigquery_loader")


# ---------------------------------------------------------------------------
# BigQuery schema definition
# ---------------------------------------------------------------------------

_SCHEMA = [
    {"name": "date", "type": "DATE", "mode": "REQUIRED"},
    {"name": "platform", "type": "STRING", "mode": "REQUIRED"},
    {"name": "campaign_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "campaign_name", "type": "STRING", "mode": "REQUIRED"},
    {"name": "impressions", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "clicks", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "spend", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "conversions", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "revenue", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "cost_per_click", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "click_through_rate", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "cost_per_conversion", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "roas", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "updated_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
]

# Local CSV path
_LOCAL_CSV = "ad_performance_data.csv"


class BigQueryLoader:
    """Manages the BigQuery table and handles data loading/reading."""

    def __init__(self) -> None:
        self._client = None
        self._config = settings.bigquery
        self._local_path = settings.app.data_dir / _LOCAL_CSV

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Set up the BigQuery client and ensure the dataset/table exist.
        Skipped entirely in local mode.
        """
        if settings.app.local_mode:
            logger.info("Running in local mode — BigQuery disabled")
            settings.app.data_dir.mkdir(parents=True, exist_ok=True)
            return

        if not self._config.is_configured:
            raise RuntimeError(
                "BigQuery not configured. Set GCP_PROJECT_ID or enable LOCAL_MODE."
            )

        try:
            from google.cloud import bigquery

            self._client = bigquery.Client(project=self._config.project_id)
            self._ensure_dataset()
            self._ensure_table()
            logger.info("BigQuery initialized: %s", self._config.full_table_id)
        except Exception as e:
            logger.error("Failed to initialize BigQuery: %s", e)
            raise

    def _ensure_dataset(self) -> None:
        """Create the dataset if it doesn't exist."""
        from google.cloud import bigquery
        from google.api_core.exceptions import Conflict

        dataset_ref = bigquery.DatasetReference(
            self._config.project_id, self._config.dataset
        )
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"

        try:
            self._client.create_dataset(dataset)
            logger.info("Created BigQuery dataset: %s", self._config.dataset)
        except Conflict:
            logger.debug("Dataset %s already exists", self._config.dataset)

    def _ensure_table(self) -> None:
        """Create the partitioned table if it doesn't exist."""
        from google.cloud import bigquery
        from google.api_core.exceptions import Conflict

        schema = [
            bigquery.SchemaField(f["name"], f["type"], mode=f["mode"])
            for f in _SCHEMA
        ]

        table_ref = self._client.dataset(self._config.dataset).table(
            self._config.table
        )
        table = bigquery.Table(table_ref, schema=schema)

        # Partition by date for efficient queries and cost management
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="date",
        )

        try:
            self._client.create_table(table)
            logger.info("Created BigQuery table: %s", self._config.table)
        except Conflict:
            logger.debug("Table %s already exists", self._config.table)

    # ------------------------------------------------------------------
    # Loading data
    # ------------------------------------------------------------------

    def load_data(self, df: pd.DataFrame) -> int:
        """
        Load a DataFrame into BigQuery (or local CSV).

        Adds an `updated_at` timestamp to each row before loading.
        Uses WRITE_TRUNCATE to replace existing data and keep storage
        within free-tier limits.

        Args:
            df: DataFrame with the standard ad_performance columns.

        Returns:
            Number of rows loaded.
        """
        if df.empty:
            logger.warning("No data to load — DataFrame is empty")
            return 0

        # Add timestamp
        df = df.copy()
        df["updated_at"] = datetime.utcnow().isoformat()

        if settings.app.local_mode:
            return self._load_local(df)
        else:
            return self._load_bigquery(df)

    def _load_bigquery(self, df: pd.DataFrame) -> int:
        """Load into BigQuery using the load_table_from_dataframe method."""
        from google.cloud import bigquery

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            schema=[
                bigquery.SchemaField(f["name"], f["type"], mode=f["mode"])
                for f in _SCHEMA
            ],
        )

        try:
            job = self._client.load_table_from_dataframe(
                df,
                self._config.full_table_id,
                job_config=job_config,
            )
            job.result()  # Wait for completion
            logger.info(
                "Loaded %d rows into BigQuery table %s",
                len(df), self._config.full_table_id,
            )
            return len(df)
        except Exception as e:
            logger.error("BigQuery load failed: %s", e)
            raise

    def _load_local(self, df: pd.DataFrame) -> int:
        """Save to a local CSV file as a BigQuery stand-in."""
        settings.app.data_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(self._local_path, index=False)
        logger.info("Saved %d rows to %s", len(df), self._local_path)
        return len(df)

    # ------------------------------------------------------------------
    # Reading data (for the dashboard)
    # ------------------------------------------------------------------

    def read_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Read ad performance data from BigQuery or local CSV.

        Args:
            start_date: Optional filter — YYYY-MM-DD
            end_date:   Optional filter — YYYY-MM-DD
            platform:   Optional filter — 'google' or 'meta'

        Returns:
            Filtered DataFrame.
        """
        if settings.app.local_mode:
            return self._read_local(start_date, end_date, platform)
        else:
            return self._read_bigquery(start_date, end_date, platform)

    def _read_bigquery(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        platform: Optional[str],
    ) -> pd.DataFrame:
        """Run a query against BigQuery with optional filters."""
        conditions = []
        if start_date:
            conditions.append(f"date >= '{start_date}'")
        if end_date:
            conditions.append(f"date <= '{end_date}'")
        if platform:
            conditions.append(f"platform = '{platform}'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT *
            FROM `{self._config.full_table_id}`
            {where_clause}
            ORDER BY date DESC, platform, campaign_name
        """

        try:
            df = self._client.query(query).to_dataframe()
            logger.info("Read %d rows from BigQuery", len(df))
            return df
        except Exception as e:
            logger.error("BigQuery read failed: %s", e)
            raise

    def _read_local(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        platform: Optional[str],
    ) -> pd.DataFrame:
        """Read from the local CSV file with optional filters."""
        if not self._local_path.exists():
            logger.warning("Local data file not found: %s", self._local_path)
            return pd.DataFrame()

        df = pd.read_csv(self._local_path, parse_dates=["date"])
        df["date"] = pd.to_datetime(df["date"]).dt.date

        if start_date:
            df = df[df["date"] >= pd.to_datetime(start_date).date()]
        if end_date:
            df = df[df["date"] <= pd.to_datetime(end_date).date()]
        if platform:
            df = df[df["platform"] == platform]

        logger.info("Read %d rows from local CSV", len(df))
        return df

    # ------------------------------------------------------------------
    # Schema info
    # ------------------------------------------------------------------

    @staticmethod
    def get_schema() -> list[dict]:
        """Return the BigQuery schema definition."""
        return _SCHEMA.copy()
