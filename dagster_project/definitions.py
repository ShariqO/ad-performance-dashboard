"""
Dagster Definitions (Entrypoint)
=================================
Bundles assets, dbt resources, jobs, and schedules into a single Dagster Definitions object.
"""

from pathlib import Path
from dagster import Definitions, load_assets_from_modules
from dagster_dbt import DbtCliResource

from dagster_project import assets
from dagster_project.schedules import daily_pipeline_schedule

# Path to dbt project
DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent / "dbt_project"

# Load non-dbt assets
python_assets = load_assets_from_modules([assets])

defs = Definitions(
    assets=[*python_assets],
    schedules=[daily_pipeline_schedule],
    resources={
        "dbt": DbtCliResource(
            project_dir=str(DBT_PROJECT_DIR),
            profiles_dir=str(DBT_PROJECT_DIR),
        ),
    },
)
