"""
Centralized configuration for the Ad Performance Dashboard.

Loads all settings from environment variables (via .env file) and exposes
them as typed dataclasses. Import `settings` from this module to access
the active configuration anywhere in the project.

Usage:
    from config.settings import settings
    print(settings.snowflake.account)
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file from the project root
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _env(key: str, default: str | None = None, required: bool = False) -> str:
    """Read an environment variable with optional default and validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(
            f"Missing required environment variable: {key}. "
            f"Copy .env.example to .env and fill in your values."
        )
    return value or ""


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GoogleAdsConfig:
    """Google Ads API credentials and settings."""
    developer_token: str = field(default_factory=lambda: _env("GOOGLE_ADS_DEVELOPER_TOKEN"))
    client_id: str = field(default_factory=lambda: _env("GOOGLE_ADS_CLIENT_ID"))
    client_secret: str = field(default_factory=lambda: _env("GOOGLE_ADS_CLIENT_SECRET"))
    refresh_token: str = field(default_factory=lambda: _env("GOOGLE_ADS_REFRESH_TOKEN"))
    login_customer_id: str = field(default_factory=lambda: _env("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))
    customer_id: str = field(default_factory=lambda: _env("GOOGLE_ADS_CUSTOMER_ID"))

    @property
    def is_configured(self) -> bool:
        """Return True if all required credentials are present."""
        return all([
            self.developer_token,
            self.client_id,
            self.client_secret,
            self.refresh_token,
            self.customer_id,
        ])


@dataclass(frozen=True)
class MetaAdsConfig:
    """Meta (Facebook) Ads API credentials and settings."""
    app_id: str = field(default_factory=lambda: _env("META_APP_ID"))
    app_secret: str = field(default_factory=lambda: _env("META_APP_SECRET"))
    access_token: str = field(default_factory=lambda: _env("META_ACCESS_TOKEN"))
    ad_account_id: str = field(default_factory=lambda: _env("META_AD_ACCOUNT_ID"))

    @property
    def is_configured(self) -> bool:
        """Return True if all required credentials are present."""
        return all([
            self.app_id,
            self.app_secret,
            self.access_token,
            self.ad_account_id,
        ])


@dataclass(frozen=True)
class SnowflakeConfig:
    """Snowflake settings and connection configuration."""
    account: str = field(default_factory=lambda: _env("SNOWFLAKE_ACCOUNT"))
    user: str = field(default_factory=lambda: _env("SNOWFLAKE_USER"))
    private_key_path: str = field(
        default_factory=lambda: _env("SNOWFLAKE_PRIVATE_KEY_PATH", "credentials/snowflake_key.p8")
    )
    warehouse: str = field(default_factory=lambda: _env("SNOWFLAKE_WAREHOUSE", "AD_PIPELINE_WH"))
    database: str = field(default_factory=lambda: _env("SNOWFLAKE_DATABASE", "AD_PERFORMANCE"))
    schema: str = field(default_factory=lambda: _env("SNOWFLAKE_SCHEMA", "RAW"))
    table: str = field(default_factory=lambda: _env("SNOWFLAKE_TABLE", "AD_METRICS"))

    @property
    def is_configured(self) -> bool:
        """Return True if Snowflake credentials are set."""
        return bool(self.account and self.user)


@dataclass(frozen=True)
class AppConfig:
    """General application settings."""
    lookback_days: int = field(
        default_factory=lambda: int(_env("LOOKBACK_DAYS", "30"))
    )
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    use_mock_data: bool = field(
        default_factory=lambda: _env("USE_MOCK_DATA", "true").lower() == "true"
    )
    data_dir: Path = field(default_factory=lambda: _project_root / "data")

    @property
    def start_date(self) -> str:
        """Return the start date string (YYYY-MM-DD) based on lookback_days."""
        dt = datetime.now() - timedelta(days=self.lookback_days)
        return dt.strftime("%Y-%m-%d")

    @property
    def end_date(self) -> str:
        """Return yesterday's date string (YYYY-MM-DD)."""
        dt = datetime.now() - timedelta(days=1)
        return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Top-level settings singleton
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Root configuration object that aggregates all sub-configs."""
    google_ads: GoogleAdsConfig = field(default_factory=GoogleAdsConfig)
    meta_ads: MetaAdsConfig = field(default_factory=MetaAdsConfig)
    snowflake: SnowflakeConfig = field(default_factory=SnowflakeConfig)
    app: AppConfig = field(default_factory=AppConfig)


# Instantiate once — import this everywhere
settings = Settings()


# ---------------------------------------------------------------------------
# Configure logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure the root logger for the project and return it."""
    log_level = getattr(logging, settings.app.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Quieten noisy third-party loggers
    logging.getLogger("google.ads").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("snowflake.connector").setLevel(logging.WARNING)

    logger = logging.getLogger("ad_dashboard")
    logger.info("Configuration loaded successfully")
    logger.debug("Mock mode: %s", settings.app.use_mock_data)
    logger.debug("Date range: %s → %s", settings.app.start_date, settings.app.end_date)

    return logger
