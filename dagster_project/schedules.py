"""
Dagster Schedules
=================
Defines recurring daily schedule for the ad performance data pipeline.
"""

from dagster import ScheduleDefinition, define_asset_job

# Define asset job that runs the entire pipeline (extraction -> load -> dbt)
daily_pipeline_job = define_asset_job(
    name="daily_ad_performance_pipeline_job",
    selection="*",
)

# Run daily at 06:00 AM UTC
daily_pipeline_schedule = ScheduleDefinition(
    job=daily_pipeline_job,
    cron_schedule="0 6 * * *",
    execution_timezone="UTC",
)
