# ============================================================
# Ad Performance Dashboard — Docker
# ============================================================
# Multi-purpose image: runs either the ETL pipeline or the
# Streamlit dashboard depending on the command.
#
# Build:   docker build -t ad-dashboard .
# Pipeline: docker run --env-file .env ad-dashboard python run_pipeline.py --mock --local
# Dashboard: docker run --env-file .env -p 8501:8501 ad-dashboard
# ============================================================

FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies (layer cached separately from source code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create data directory for local mode
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Health check for the dashboard
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default: run the Streamlit dashboard
CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
