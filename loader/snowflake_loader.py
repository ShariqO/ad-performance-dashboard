"""
Snowflake Loader — Loads raw ad performance data into Snowflake
================================================================
Uses MERGE (upsert) on campaign_id + date to prevent duplicate records
on pipeline reruns. Connects via RSA key-pair authentication.

Usage:
    loader = SnowflakeLoader()
    loader.initialize()
    rows = loader.load_data(df)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger("ad_dashboard.snowflake_loader")


class SnowflakeLoader:
    """Manages Snowflake connection and data loading with MERGE upsert."""

    def __init__(self):
        self._account = os.getenv("SNOWFLAKE_ACCOUNT", "")
        self._user = os.getenv("SNOWFLAKE_USER", "")
        self._private_key_path = os.getenv(
            "SNOWFLAKE_PRIVATE_KEY_PATH", "credentials/snowflake_key.p8"
        )
        self._warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "AD_PIPELINE_WH")
        self._database = os.getenv("SNOWFLAKE_DATABASE", "AD_PERFORMANCE")
        self._schema = os.getenv("SNOWFLAKE_SCHEMA", "RAW")
        self._table = os.getenv("SNOWFLAKE_TABLE", "AD_METRICS")
        self._conn: snowflake.connector.SnowflakeConnection | None = None

    def _load_private_key(self) -> bytes:
        """Load RSA private key and return DER-encoded bytes."""
        key_path = Path(self._private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(
                f"Snowflake private key not found: {key_path}. "
                "Generate one with: openssl genrsa 2048 | openssl pkcs8 -topk8 "
                "-inform PEM -out credentials/snowflake_key.p8 -nocrypt"
            )
        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )
        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def initialize(self) -> None:
        """Establish connection and ensure the target table exists."""
        if not self._account or not self._user:
            raise ValueError(
                "Snowflake credentials not configured — "
                "set SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER in .env"
            )

        logger.info("Connecting to Snowflake: %s.%s.%s", self._database, self._schema, self._table)

        pkb = self._load_private_key()
        self._conn = snowflake.connector.connect(
            user=self._user,
            account=self._account,
            private_key=pkb,
            warehouse=self._warehouse,
            database=self._database,
            schema=self._schema,
        )

        # Ensure table exists
        self._conn.cursor().execute(f"""
            CREATE TABLE IF NOT EXISTS {self._database}.{self._schema}.{self._table} (
                date DATE NOT NULL,
                platform VARCHAR(20) NOT NULL,
                campaign_id VARCHAR(100) NOT NULL,
                campaign_name VARCHAR(255) NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                spend FLOAT DEFAULT 0.0,
                conversions FLOAT DEFAULT 0.0,
                revenue FLOAT DEFAULT 0.0,
                updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (campaign_id, date)
            )
        """)

        logger.info(
            "Snowflake initialized: %s.%s.%s",
            self._database, self._schema, self._table,
        )

    def load_data(self, df: pd.DataFrame) -> int:
        """
        Load data into Snowflake using MERGE (upsert).

        Rows are matched on (campaign_id, date). Matching rows are updated;
        new rows are inserted. This prevents duplicates on pipeline reruns.

        Args:
            df: DataFrame with columns: date, platform, campaign_id,
                campaign_name, impressions, clicks, spend, conversions, revenue

        Returns:
            Number of rows affected (inserted + updated).
        """
        if df.empty:
            logger.warning("Empty DataFrame — nothing to load")
            return 0

        if self._conn is None:
            raise RuntimeError("Call initialize() before load_data()")

        cur = self._conn.cursor()

        # Create a temporary staging table for the incoming batch
        staging_table = f"{self._table}_STAGING"
        fqn_staging = f"{self._database}.{self._schema}.{staging_table}"
        fqn_target = f"{self._database}.{self._schema}.{self._table}"

        try:
            # Create temp staging table with same structure
            cur.execute(f"CREATE TEMPORARY TABLE IF NOT EXISTS {fqn_staging} LIKE {fqn_target}")
            cur.execute(f"TRUNCATE TABLE {fqn_staging}")

            # Add updated_at column to the dataframe
            df = df.copy()
            df["updated_at"] = pd.Timestamp.utcnow()

            # Insert data into staging table using parameterized inserts
            insert_sql = f"""
                INSERT INTO {fqn_staging}
                (date, platform, campaign_id, campaign_name,
                 impressions, clicks, spend, conversions, revenue, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            rows = [
                (
                    str(row["date"]),
                    row["platform"],
                    str(row["campaign_id"]),
                    row["campaign_name"],
                    int(row["impressions"]),
                    int(row["clicks"]),
                    float(row["spend"]),
                    float(row["conversions"]),
                    float(row["revenue"]),
                    row["updated_at"].to_pydatetime(),
                )
                for _, row in df.iterrows()
            ]

            cur.executemany(insert_sql, rows)
            logger.info("Staged %d rows into %s", len(rows), fqn_staging)

            # MERGE: upsert from staging into target
            merge_sql = f"""
                MERGE INTO {fqn_target} AS target
                USING {fqn_staging} AS source
                ON target.campaign_id = source.campaign_id
                   AND target.date = source.date
                WHEN MATCHED THEN UPDATE SET
                    target.platform = source.platform,
                    target.campaign_name = source.campaign_name,
                    target.impressions = source.impressions,
                    target.clicks = source.clicks,
                    target.spend = source.spend,
                    target.conversions = source.conversions,
                    target.revenue = source.revenue,
                    target.updated_at = source.updated_at
                WHEN NOT MATCHED THEN INSERT
                    (date, platform, campaign_id, campaign_name,
                     impressions, clicks, spend, conversions, revenue, updated_at)
                VALUES
                    (source.date, source.platform, source.campaign_id, source.campaign_name,
                     source.impressions, source.clicks, source.spend, source.conversions,
                     source.revenue, source.updated_at)
            """

            cur.execute(merge_sql)

            # Get rows affected
            cur.execute(f"SELECT COUNT(*) FROM {fqn_target}")
            total_rows = cur.fetchone()[0]

            logger.info(
                "MERGE complete — %d rows staged, %d total rows in %s",
                len(rows), total_rows, fqn_target,
            )
            return len(rows)

        except Exception as e:
            logger.error("Snowflake load failed: %s", e)
            raise
        finally:
            cur.close()

    def query(self, sql: str) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame."""
        if self._conn is None:
            raise RuntimeError("Call initialize() before query()")

        cur = self._conn.cursor()
        try:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            return pd.DataFrame(data, columns=columns)
        finally:
            cur.close()

    def close(self) -> None:
        """Close the Snowflake connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Snowflake connection closed")
