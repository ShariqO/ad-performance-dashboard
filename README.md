# Ad Performance Dashboard

An ELT pipeline and dashboard for campaign performance data from Meta Ads and Google Ads. Extracts from both platform APIs, loads into Snowflake, transforms with dbt, orchestrates with Dagster, and visualises in Streamlit.

## A note on the data

The repo contains working API connectors for the Meta Marketing API and the Google Ads API (GAQL), but neither returns useful data for a personal project:

- **Meta Marketing API** authenticates fine over OAuth, but the personal ad account has no spend history, so the API returns zero records.
- **Google Ads API** is limited to the Test Account tier, which is a sandbox for UI navigation rather than programmatic retrieval. Production access needs a verified business domain.

So the pipeline runs on a seeded mock data generator covering 7 campaigns over 30 consecutive days. The connectors are still in the codebase and still work; they just have nothing to return.

## Architecture

**Extract.** Python connectors pull campaign-level metrics (spend, clicks, impressions, conversions, revenue) from both platforms.

**Load.** `SnowflakeLoader` authenticates with an RSA key pair and runs a SQL `MERGE` on `(campaign_id, date)`. Reruns update existing rows rather than appending duplicates.

**Transform.** A three-layer dbt project:

- *Staging*: `stg_google_ads`, `stg_meta_ads`. Standardise schemas, trim strings, handle nulls
- *Intermediate*: `int_campaigns_unioned`. Union the two platform datasets
- *Marts*: `dim_campaign`, `fct_campaign_performance`, `fct_daily_platform_summary`. Derived metrics (CPC, CTR, cost per conversion, ROAS)

**Orchestrate.** Dagster software-defined assets handle the dependency graph, retries, and a daily schedule (`0 6 * * *`). dbt models are pulled in as assets via `dagster-dbt`.

**Visualise.** Streamlit queries the mart tables through `snowflake-connector-python`.

## dbt layer

Six models, sixteen tests.

| Layer | Model | Materialization | Purpose |
|---|---|---|---|
| Staging | `stg_google_ads` | View | Clean Google Ads metrics |
| Staging | `stg_meta_ads` | View | Clean Meta Ads metrics |
| Intermediate | `int_campaigns_unioned` | View | Union both platforms into one schema |
| Marts | `dim_campaign` | Table | Campaign metadata, first/last seen, active days |
| Marts | `fct_campaign_performance` | Table | Daily performance with CPC, CTR, cost per conversion, ROAS |
| Marts | `fct_daily_platform_summary` | Table | Platform-level daily rollups |

Tests cover primary key uniqueness and non-null on `dim_campaign.campaign_id` and the composite keys, an `accepted_values` check on `int_campaigns_unioned.platform`, a `relationships` test asserting every `fct_campaign_performance.campaign_id` exists in `dim_campaign`, and not-null assertions across date, spend, and metric columns.

```bash
cd dbt_project
dbt test --profiles-dir .
```

## Why it's built this way

**MERGE instead of full overwrite.** The loader stages extracts into a temp table and merges on `(campaign_id, date)`. A full `WRITE_TRUNCATE` would have been simpler, but reruns and backfills are normal in this kind of pipeline and I wanted them to be safe by default rather than something you have to think about.

**Dagster over Airflow.** Airflow models a pipeline as a graph of tasks, where the data moving between them is implicit. Dagster models it as a graph of assets, so each step declares what table it produces and what it depends on. For a dbt-centric project that mapping is close to one-to-one, and `dagster-dbt` pulls every dbt model into the same graph.

**Three dbt layers.** Staging does renaming and type casting only, so downstream models are insulated from source quirks. Intermediate holds anything reused across marts. Marts hold facts and dimensions, with the arithmetic (ROAS, CTR) pushed down into SQL rather than computed in the dashboard.

## Running it

Requires Python 3.10+ and a Snowflake account.

```bash
git clone https://github.com/ShariqO/ad-performance-dashboard.git
cd ad-performance-dashboard

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Generate an RSA key pair for Snowflake:

```bash
mkdir -p credentials
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out credentials/snowflake_key.p8 -nocrypt
openssl rsa -in credentials/snowflake_key.p8 -pubout -out credentials/snowflake_key.pub
```

Attach the public key to your Snowflake user:

```sql
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='<contents of snowflake_key.pub, no header/footer>';
```

Then copy `.env.example` to `.env` and fill in your credentials.

Run the pipeline:

```bash
dagster dev -w workspace.yaml      # UI at localhost:3000
streamlit run dashboard/app.py     # dashboard at localhost:8501
```

Or with Docker:

```bash
docker-compose up --build
```

## Project structure

```
ad-performance-dashboard/
├── connectors/          # Google Ads and Meta Ads API clients + mock generators
├── loader/              # Snowflake loader (MERGE upsert, key-pair auth)
├── dbt_project/
│   ├── models/          # staging, intermediate, marts
│   └── macros/          # custom schema routing
├── dagster_project/     # assets, definitions, schedules
├── dashboard/           # Streamlit app
├── config/              # environment config and logging
└── .github/workflows/
```

## License

MIT.
