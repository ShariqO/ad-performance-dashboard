"""
Ad Performance Dashboard
========================
A Streamlit dashboard that visualizes ad campaign performance across
Google Ads and Meta (Facebook) Ads.

Features:
    - KPI cards with delta indicators
    - Interactive charts (spend trends, CTR, CPC, conversions)
    - Platform comparison
    - Campaign-level performance table
    - Sidebar filters for date range, platform, and campaign

Run locally:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path so imports work when running from any dir
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from config.settings import settings
from pipeline.bigquery_loader import BigQueryLoader
from pipeline.transform import TransformPipeline

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Ad Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a premium dark theme
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* ---- Global ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ---- KPI cards ---- */
    .kpi-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .kpi-label {
        font-size: 13px;
        font-weight: 500;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: #e6f1ff;
        margin-bottom: 4px;
    }
    .kpi-delta-positive {
        font-size: 14px;
        font-weight: 500;
        color: #64ffda;
    }
    .kpi-delta-negative {
        font-size: 14px;
        font-weight: 500;
        color: #ff6b6b;
    }

    /* ---- Section headers ---- */
    .section-header {
        font-size: 20px;
        font-weight: 600;
        color: #ccd6f6;
        margin: 32px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(100, 255, 218, 0.2);
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a192f 0%, #112240 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #8892b0;
    }

    /* ---- Data table styling ---- */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }

    /* ---- Hide Streamlit branding ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ---- Chart containers ---- */
    .chart-container {
        background: rgba(17, 34, 64, 0.5);
        border-radius: 16px;
        padding: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data() -> pd.DataFrame:
    """Load and transform ad performance data."""
    loader = BigQueryLoader()
    loader.initialize()

    df = loader.read_data()

    if df.empty:
        return df

    # Ensure date column is proper datetime
    df["date"] = pd.to_datetime(df["date"])

    # Run transformations if derived columns are missing
    if "cost_per_click" not in df.columns or df["cost_per_click"].isna().all():
        pipeline = TransformPipeline()
        df = pipeline.run(df)

    return df


def format_currency(value: float) -> str:
    """Format a number as currency."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}K"
    else:
        return f"${value:.2f}"


def format_number(value: float) -> str:
    """Format a large number with K/M suffixes."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:,.0f}"


# ---------------------------------------------------------------------------
# Plotly theme
# ---------------------------------------------------------------------------

_COLORS = {
    "google": "#4285F4",     # Google blue
    "meta": "#0668E1",       # Meta blue
    "accent": "#64ffda",     # Teal accent
    "bg": "#0a192f",         # Dark background
    "card_bg": "#112240",    # Card background
    "text": "#ccd6f6",       # Primary text
    "text_muted": "#8892b0", # Muted text
    "positive": "#64ffda",   # Green
    "negative": "#ff6b6b",   # Red
}

_PLATFORM_COLORS = {"google": "#4285F4", "meta": "#0668E1"}

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=_COLORS["text"], size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        zerolinecolor="rgba(255,255,255,0.05)",
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        zerolinecolor="rgba(255,255,255,0.05)",
    ),
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def main():
    """Render the full dashboard."""

    # ---- Header ----
    st.markdown(
        "<h1 style='color: #e6f1ff; font-weight: 700; margin-bottom: 4px;'>"
        "📊 Ad Performance Dashboard</h1>"
        "<p style='color: #8892b0; font-size: 16px; margin-bottom: 32px;'>"
        "Cross-platform campaign analytics — Google Ads & Meta Ads</p>",
        unsafe_allow_html=True,
    )

    # ---- Load data ----
    df = load_data()

    if df.empty:
        st.warning(
            "⚠️ No data found. Run the pipeline first:\n\n"
            "```bash\npython run_pipeline.py --mock --local\n```"
        )
        st.stop()

    # ---- Sidebar filters ----
    with st.sidebar:
        st.markdown(
            "<h2 style='color: #e6f1ff; font-size: 18px;'>🎛️ Filters</h2>",
            unsafe_allow_html=True,
        )

        # Date range
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()

        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="date_filter",
        )

        # Platform filter
        platforms = ["All"] + sorted(df["platform"].unique().tolist())
        selected_platform = st.selectbox(
            "Platform",
            platforms,
            key="platform_filter",
        )

        # Campaign filter
        if selected_platform != "All":
            available_campaigns = sorted(
                df[df["platform"] == selected_platform]["campaign_name"].unique()
            )
        else:
            available_campaigns = sorted(df["campaign_name"].unique())

        selected_campaigns = st.multiselect(
            "Campaigns",
            available_campaigns,
            default=available_campaigns,
            key="campaign_filter",
        )

        st.markdown("---")
        st.markdown(
            "<p style='color: #8892b0; font-size: 12px;'>"
            "Data refreshes every 5 minutes.<br>"
            f"Last loaded: {datetime.now().strftime('%H:%M:%S')}</p>",
            unsafe_allow_html=True,
        )

    # ---- Apply filters ----
    filtered_df = df.copy()

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered_df = filtered_df[
            (filtered_df["date"].dt.date >= start)
            & (filtered_df["date"].dt.date <= end)
        ]

    if selected_platform != "All":
        filtered_df = filtered_df[filtered_df["platform"] == selected_platform]

    if selected_campaigns:
        filtered_df = filtered_df[
            filtered_df["campaign_name"].isin(selected_campaigns)
        ]

    if filtered_df.empty:
        st.info("No data matches the current filters.")
        st.stop()

    # ---- KPI Cards ----
    render_kpi_cards(filtered_df)

    # ---- Charts ----
    st.markdown(
        '<div class="section-header">📈 Performance Trends</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        render_spend_trend(filtered_df)
    with col2:
        render_ctr_trend(filtered_df)

    col3, col4 = st.columns(2)
    with col3:
        render_cpc_comparison(filtered_df)
    with col4:
        render_platform_split(filtered_df)

    # ---- Conversions chart ----
    st.markdown(
        '<div class="section-header">🎯 Conversions & ROAS</div>',
        unsafe_allow_html=True,
    )

    col5, col6 = st.columns(2)
    with col5:
        render_conversions_trend(filtered_df)
    with col6:
        render_roas_comparison(filtered_df)

    # ---- Campaign table ----
    st.markdown(
        '<div class="section-header">📋 Campaign Details</div>',
        unsafe_allow_html=True,
    )
    render_campaign_table(filtered_df)


# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------

def render_kpi_cards(df: pd.DataFrame) -> None:
    """Render the top-row KPI summary cards with deltas."""

    # Calculate current period totals
    total_spend = df["spend"].sum()
    total_clicks = df["clicks"].sum()
    total_impressions = df["impressions"].sum()
    total_conversions = df["conversions"].sum()
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    avg_roas = (df["revenue"].sum() / total_spend) if total_spend > 0 else 0
    avg_cpconv = (total_spend / total_conversions) if total_conversions > 0 else 0

    # Calculate deltas (compare first half vs second half of period)
    midpoint = df["date"].min() + (df["date"].max() - df["date"].min()) / 2
    first_half = df[df["date"] <= midpoint]
    second_half = df[df["date"] > midpoint]

    def calc_delta(metric: str) -> float:
        fh = first_half[metric].sum()
        sh = second_half[metric].sum()
        if fh == 0:
            return 0
        return ((sh - fh) / fh) * 100

    spend_delta = calc_delta("spend")
    clicks_delta = calc_delta("clicks")
    conv_delta = calc_delta("conversions")

    kpis = [
        ("Total Spend", format_currency(total_spend), spend_delta),
        ("Total Clicks", format_number(total_clicks), clicks_delta),
        ("Avg CTR", f"{avg_ctr:.2f}%", None),
        ("Avg CPC", f"${avg_cpc:.2f}", None),
        ("Conversions", format_number(total_conversions), conv_delta),
        ("ROAS", f"{avg_roas:.2f}x", None),
    ]

    cols = st.columns(6)
    for col, (label, value, delta) in zip(cols, kpis):
        delta_html = ""
        if delta is not None:
            css_class = "kpi-delta-positive" if delta >= 0 else "kpi-delta-negative"
            arrow = "↑" if delta >= 0 else "↓"
            delta_html = (
                f'<div class="{css_class}">{arrow} {abs(delta):.1f}% vs prior period</div>'
            )

        col.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                {delta_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def render_spend_trend(df: pd.DataFrame) -> None:
    """Daily spend trend line chart by platform."""
    daily = (
        df.groupby(["date", "platform"])["spend"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        daily,
        x="date",
        y="spend",
        color="platform",
        color_discrete_map=_PLATFORM_COLORS,
        title="Daily Ad Spend",
        labels={"spend": "Spend ($)", "date": "Date", "platform": "Platform"},
    )
    fig.update_layout(**_PLOTLY_LAYOUT)
    fig.update_traces(line=dict(width=2.5))
    st.plotly_chart(fig, use_container_width=True)


def render_ctr_trend(df: pd.DataFrame) -> None:
    """Daily CTR trend by platform."""
    daily = (
        df.groupby(["date", "platform"])
        .agg({"clicks": "sum", "impressions": "sum"})
        .reset_index()
    )
    daily["ctr"] = (daily["clicks"] / daily["impressions"].replace(0, float("nan"))) * 100

    fig = px.line(
        daily,
        x="date",
        y="ctr",
        color="platform",
        color_discrete_map=_PLATFORM_COLORS,
        title="Daily Click-Through Rate",
        labels={"ctr": "CTR (%)", "date": "Date", "platform": "Platform"},
    )
    fig.update_layout(**_PLOTLY_LAYOUT)
    fig.update_traces(line=dict(width=2.5))
    st.plotly_chart(fig, use_container_width=True)


def render_cpc_comparison(df: pd.DataFrame) -> None:
    """Average CPC by campaign (bar chart)."""
    camp_metrics = (
        df.groupby(["campaign_name", "platform"])
        .agg({"spend": "sum", "clicks": "sum"})
        .reset_index()
    )
    camp_metrics["cpc"] = (
        camp_metrics["spend"] / camp_metrics["clicks"].replace(0, float("nan"))
    ).round(2)

    fig = px.bar(
        camp_metrics.sort_values("cpc", ascending=True),
        x="cpc",
        y="campaign_name",
        color="platform",
        color_discrete_map=_PLATFORM_COLORS,
        orientation="h",
        title="Cost Per Click by Campaign",
        labels={
            "cpc": "CPC ($)",
            "campaign_name": "",
            "platform": "Platform",
        },
    )
    fig.update_layout(**_PLOTLY_LAYOUT)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig, use_container_width=True)


def render_platform_split(df: pd.DataFrame) -> None:
    """Spend distribution pie chart by platform."""
    platform_spend = df.groupby("platform")["spend"].sum().reset_index()

    fig = px.pie(
        platform_spend,
        values="spend",
        names="platform",
        color="platform",
        color_discrete_map=_PLATFORM_COLORS,
        title="Spend Distribution by Platform",
        hole=0.4,
    )
    fig.update_layout(**_PLOTLY_LAYOUT)
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=14,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_conversions_trend(df: pd.DataFrame) -> None:
    """Daily conversions trend by platform."""
    daily = (
        df.groupby(["date", "platform"])["conversions"]
        .sum()
        .reset_index()
    )

    fig = px.area(
        daily,
        x="date",
        y="conversions",
        color="platform",
        color_discrete_map=_PLATFORM_COLORS,
        title="Daily Conversions",
        labels={
            "conversions": "Conversions",
            "date": "Date",
            "platform": "Platform",
        },
    )
    fig.update_layout(**_PLOTLY_LAYOUT)
    fig.update_traces(line=dict(width=2))
    st.plotly_chart(fig, use_container_width=True)


def render_roas_comparison(df: pd.DataFrame) -> None:
    """ROAS by campaign (bar chart)."""
    camp_metrics = (
        df.groupby(["campaign_name", "platform"])
        .agg({"revenue": "sum", "spend": "sum"})
        .reset_index()
    )
    camp_metrics["roas"] = (
        camp_metrics["revenue"] / camp_metrics["spend"].replace(0, float("nan"))
    ).round(2)

    fig = px.bar(
        camp_metrics.sort_values("roas", ascending=True),
        x="roas",
        y="campaign_name",
        color="platform",
        color_discrete_map=_PLATFORM_COLORS,
        orientation="h",
        title="Return on Ad Spend (ROAS) by Campaign",
        labels={
            "roas": "ROAS (x)",
            "campaign_name": "",
            "platform": "Platform",
        },
    )
    fig.update_layout(**_PLOTLY_LAYOUT)
    fig.update_layout(yaxis=dict(categoryorder="total ascending"))

    # Add a reference line at ROAS = 1.0 (break-even)
    fig.add_vline(
        x=1.0,
        line_dash="dash",
        line_color=_COLORS["negative"],
        annotation_text="Break-even",
        annotation_font_color=_COLORS["text_muted"],
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Campaign table
# ---------------------------------------------------------------------------

def render_campaign_table(df: pd.DataFrame) -> None:
    """Sortable campaign performance summary table."""

    table_df = (
        df.groupby(["platform", "campaign_id", "campaign_name"])
        .agg({
            "impressions": "sum",
            "clicks": "sum",
            "spend": "sum",
            "conversions": "sum",
            "revenue": "sum",
        })
        .reset_index()
    )

    # Recalculate ratios on aggregated data
    table_df["CPC"] = (
        table_df["spend"] / table_df["clicks"].replace(0, float("nan"))
    ).round(2)
    table_df["CTR (%)"] = (
        table_df["clicks"] / table_df["impressions"].replace(0, float("nan")) * 100
    ).round(2)
    table_df["Cost/Conv"] = (
        table_df["spend"] / table_df["conversions"].replace(0, float("nan"))
    ).round(2)
    table_df["ROAS"] = (
        table_df["revenue"] / table_df["spend"].replace(0, float("nan"))
    ).round(2)

    # Format for display
    display_df = table_df[[
        "platform", "campaign_name", "impressions", "clicks",
        "spend", "conversions", "CPC", "CTR (%)", "Cost/Conv", "ROAS",
    ]].rename(columns={
        "platform": "Platform",
        "campaign_name": "Campaign",
        "impressions": "Impressions",
        "clicks": "Clicks",
        "spend": "Spend ($)",
        "conversions": "Conversions",
    })

    display_df = display_df.sort_values("Spend ($)", ascending=False)
    display_df = display_df.fillna(0)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Platform": st.column_config.TextColumn(width="small"),
            "Campaign": st.column_config.TextColumn(width="medium"),
            "Impressions": st.column_config.NumberColumn(format="%d"),
            "Clicks": st.column_config.NumberColumn(format="%d"),
            "Spend ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Conversions": st.column_config.NumberColumn(format="%.1f"),
            "CPC": st.column_config.NumberColumn(format="$%.2f"),
            "CTR (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Cost/Conv": st.column_config.NumberColumn(format="$%.2f"),
            "ROAS": st.column_config.NumberColumn(format="%.2fx"),
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
