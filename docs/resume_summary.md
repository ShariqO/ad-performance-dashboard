# 📄 Ad Performance Dashboard — Resume & Interview Summary

Use this document when preparing your resume bullets, LinkedIn project descriptions, or interview stories for Data Engineering roles.

---

## 📌 One-Line Project Summary

> *"Architected an end-to-end multi-platform ad performance data pipeline using Python connectors, Snowflake, dbt (6 models, 16 tests), Dagster orchestration, and an interactive Streamlit dashboard."*

---

## 📝 Detailed Paragraph (for LinkedIn / Portfolio Bio)

> *"Designed and built a modern data engineering pipeline that aggregates cross-platform campaign analytics from Google Ads and Meta Ads. Data is extracted via Python connectors, loaded into Snowflake using RSA key-pair authentication and SQL MERGE upserts to prevent duplicate records, and transformed across a 3-layer dbt architecture (Staging → Intermediate → Marts) featuring 16 automated data quality tests. The full lineage and daily scheduling are managed via Dagster Software-Defined Assets (SDAs) integrated with `dagster-dbt`, and presented to business users through an interactive Streamlit analytics dashboard."*

---

## 🎯 Resume Bullet Points (Copy & Paste to Resume)

* **Multi-Platform Ingestion:** Built custom Python API connectors for Google Ads (GAQL) and Meta Marketing API with RSA key-pair authentication into Snowflake, incorporating `MERGE` upsert statements to eliminate duplicate records on reruns.
* **dbt Data Modeling:** Designed a 3-layer dbt transformation framework (Staging, Intermediate, Marts) comprising 6 models and 16 automated dbt data quality tests (`not_null`, `unique`, `accepted_values`, `relationships`) to calculate derived ad metrics (CPC, CTR, Cost/Conversion, ROAS).
* **Dagster Orchestration:** Implemented software-defined asset (SDA) orchestration in Dagster with `dagster-dbt`, managing automated retries, daily cron scheduling (`0 6 * * *`), and full end-to-end data lineage tracking.
* **Interactive Visualization:** Developed a Streamlit web application querying Snowflake mart tables in real time, rendering executive KPI cards, Plotly spend trends, platform performance splits, and campaign-level detail tables.
* **CI/CD & Containerization:** Containerized application services using Docker Compose (Dagster Webserver, Daemon, Streamlit) and established GitHub Actions workflows for automated dbt model parsing and asset definition validation.

---

## 🗣️ Interview-Defensible Talking Points

### 1. **Why Dagster over Airflow?**
* **Airflow's limitation:** Airflow views pipelines as a series of execution tasks (`task_a >> task_b`), where what data is created or where it flows is hidden inside task Python functions.
* **Dagster's advantage:** Dagster uses **Software-Defined Assets (SDAs)**. Each asset explicitly declares *what* object it creates (e.g., `snowflake_raw_ad_metrics`) and *what* parent assets it depends on (`raw_google_ads_data`, `raw_meta_ads_data`). This allows asset-based re-materialization, native `dagster-dbt` integration where dbt models show up directly as nodes in the asset graph, and cleaner data lineage.

### 2. **Why SQL MERGE (Upsert) over Full Table Overwrites (`WRITE_TRUNCATE`)?**
* **Problem with `WRITE_TRUNCATE`:** Deletes historical data every run, which is wasteful, expensive at scale, and prevents historical trend preservation.
* **Solution with `MERGE`:** Stages incoming batch data into a temporary table in Snowflake and executes a `MERGE INTO target USING staging ON target.campaign_id = staging.campaign_id AND target.date = staging.date`. Existing campaign-day records get updated with latest values, and new days get inserted. This ensures idempotent pipeline execution without duplicate data.

### 3. **The 3-Layer dbt Pattern (Staging → Intermediate → Marts)**
* **Staging (`stg_google_ads`, `stg_meta_ads`):** 1-to-1 with raw source tables. Cleans column names, casts datatypes, trims strings, and handles NULLs without changing granularity or metric definitions.
* **Intermediate (`int_campaigns_unioned`):** Unions disparate ad platform schemas into a unified, normalized dataset.
* **Marts (`dim_campaign`, `fct_campaign_performance`, `fct_daily_platform_summary`):** Pushes business logic and metric calculations (`CPC = spend / clicks`, `ROAS = revenue / spend`) directly into Snowflake SQL engine for performance.

### 4. **How did you handle Google & Meta API constraints honestly?**
* **Google Ads API:** Google Ads tokens default to "Test Account" level, which limits querying to Test Manager accounts (a sandbox for UI navigation, not real API data). "Basic Access" to query real production accounts requires a verified corporate website.
* **Meta Marketing API:** The connector authenticates and queries live via OAuth. However, because the personal ad account has zero active spend history, live queries return 0 rows.
* **Engineering Decision:** Maintained both production-ready API connectors in the codebase for integration demonstration, while running the pipeline with a seeded mock data generator (210 rows, 7 campaigns, 30 days) so the analytics pipeline, dbt models, Snowflake warehouse, and Streamlit dashboard operate on dense, realistic metric distributions.
