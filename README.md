## Business KPI Dashboard

End-to-end data pipeline and analytics stack for a **Business KPI Dashboard**.  
The project ingests sales, customer, and product data, applies data quality checks, loads a star-schema warehouse in PostgreSQL, calculates business KPIs, and exposes them to BI tools (e.g. Power BI) and an optional REST API.

---

### Features

- **Config‑driven pipeline**: Central configuration in `config/config.yaml` for database, data sources, thresholds, and KPI targets.
- **Data ingestion**: CSV/API ingestion for sales, customers, and products via `DataIngestion`.
- **Data quality framework**: Completeness, duplicates, outliers, and business‑rule validation with scores stored in `fact_data_quality`.
- **Analytics warehouse**: PostgreSQL star schema (`dim_date`, `dim_customers`, `dim_products`, `fact_sales`, `fact_kpis`, `fact_data_quality`).
- **KPI engine**: Revenue, margin, churn, CLV, conversion, and other KPIs calculated and persisted to `fact_kpis`.
- **REST API (optional)**: Flask API to serve KPIs, data quality metrics, sales summaries, and dashboard aggregates.
- **Scheduling**: Automated runs using the `schedule` package (`src/scheduler.py`).
- **Monitoring & alerts**: Central logging (`data/logs`) and pluggable email alert system.

---

### Project Structure

```text
KPI Dashboard/
  config/
    config.yaml           # DB config, data sources, quality thresholds, KPI targets, schedule options
  data/
    raw/                  # Input CSVs (sales, customers, products)
    processed/            # Reserved for intermediate outputs
    logs/                 # Pipeline and scheduler logs
  powerbi/                # Power BI report files / templates (connect to DB views)
  sql/
    schema.sql            # Warehouse DDL + views for BI
    queries,sql           # Example analytical queries
  src/
    main.py               # Main pipeline orchestrator / CLI entrypoint
    api.py                # Optional Flask REST API for KPIs and metrics
    ingestion.py          # Data ingestion from CSVs/APIs
    data_quality.py       # Data quality checks and scoring
    kpi_calculator.py     # Business KPI computation and persistence
    database.py           # SQLAlchemy DB layer and utilities
    scheduler.py          # Automated pipeline scheduler
    email_alerts.py       # Email notification helper
    logging_config.py     # Central logging configuration utilities
  test_pipeline.py        # End‑to‑end environment / health test script
```

---

### Core Architecture

- **Orchestration layer (`DataPipeline` in `src/main.py`)**
  - Loads configuration from `config/config.yaml`.
  - Initializes `DatabaseManager`, `DataIngestion`, `DataQualityChecker`, and `KPICalculator`.
  - Implements the high‑level flow:
    1. *Optional*: Initialize DB schema and date dimension (`initialize_database`).
    2. Ingest raw data (`ingest_data`).
    3. Run data quality checks and compute scores (`run_quality_checks`).
    4. Load cleaned data into warehouse tables (`load_to_warehouse`).
    5. Compute and store KPIs (`calculate_kpis`).

- **Data ingestion (`src/ingestion.py`)**
  - Reads data sources defined in `config.yaml` under `data_sources` (either CSV `path` or HTTP `url`).
  - Normalizes column names, parses dates, and logs row counts.
  - Can generate synthetic sample data (`generate_sample_data`) for local testing.

- **Data quality (`src/data_quality.py`)**
  - Performs:
    - Completeness checks and missing‑value profiling.
    - Duplicate detection on configurable key columns.
    - Outlier detection for numeric fields using Z‑score.
    - Business‑rule validation (positive price/quantity, discount range, email format).
  - Writes quality metrics into `fact_data_quality` and detailed issues into `log_data_errors`.

- **Warehouse & database layer**
  - `sql/schema.sql` defines the warehouse schema:
    - Dimensions: `dim_date`, `dim_customers`, `dim_products`.
    - Facts: `fact_sales`, `fact_kpis`, `fact_data_quality`.
    - Logs: `log_data_errors`.
    - BI views: `vw_sales_summary`, `vw_kpi_dashboard`, `vw_data_quality_dashboard`, `vw_error_log`.
  - `DatabaseManager` (`src/database.py`):
    - Builds SQLAlchemy engine from `config.yaml`.
    - Executes schema files (`execute_sql_file`).
    - Loads `pandas` DataFrames to tables (`load_to_table`).
    - Implements dimension upsert logic and `dim_date` population.

- **KPI calculation (`src/kpi_calculator.py`)**
  - Revenue metrics: total revenue vs. target, AOV, revenue growth.
  - Customer metrics: active customers, churn rate, CLV, repeat purchase rate.
  - Product / operational metrics: items per order, profit margin, cost‑to‑revenue ratio, fulfillment.
  - Conversion metrics: customer conversion vs. target.
  - Writes results to `fact_kpis` and prints a summary report.

- **API layer (`src/api.py`)**
  - Flask app exposing:
    - `/health` – basic health and DB status.
    - `/kpis` and `/kpis/<name>` – KPI lists and historical series.
    - `/quality` – table‑level data quality dashboards.
    - `/sales/summary` – aggregate sales stats by time period.
    - `/errors` – recent data quality/error log.
    - `/dashboard/summary` – a combined snapshot for dashboard homepages.

- **Scheduling (`src/scheduler.py`)**
  - Uses `schedule` to run `DataPipeline` periodically.
  - Controlled via `schedule` section in `config/config.yaml` (enabled, frequency, time).

- **Monitoring & alerts**
  - Logging to `data/logs` (pipeline & scheduler logs) with helper utilities in `logging_config.py`.
  - `EmailAlertSystem` in `email_alerts.py` can be wired to send KPI and data‑quality alerts and daily summaries.

---

### Setup

- **Prerequisites**
  - Python 3.9+.
  - PostgreSQL instance reachable from your machine.
  - Recommended: virtual environment (e.g. `venv`).

- **Python dependencies**
  - Install the required packages (from `test_pipeline.py` expectations):

```bash
pip install pandas numpy sqlalchemy psycopg2-binary pyyaml requests schedule flask flask-cors
```

- **Database configuration**
  - Update `config/config.yaml`:
    - `database.type`: typically `postgresql`.
    - `database.host`, `port`, `database`, `username`, `password`.
    - `data_sources`: set `path` to your CSVs or `url` for APIs.
    - `quality_thresholds`, `kpi_config`, and optional `schedule` settings.

---

### Usage

- **1. Validate environment**

```bash
python test_pipeline.py
```

This checks Python packages, config file, directory layout, data files, DB connection, and DB schema.

- **2. Generate sample data (optional)**

```bash
python src/main.py --generate-data
```

Creates sample CSVs in `data/raw/` for sales, customers, and products.

- **3. Initialize the warehouse schema**

```bash
python src/main.py --init-db
```

Runs `sql/schema.sql` and populates the `dim_date` table.

- **4. Run the full pipeline**

```bash
python src/main.py
```

This will:

1. Ingest data from configured sources.  
2. Run data quality checks and write metrics.  
3. Load star‑schema tables in PostgreSQL.  
4. Calculate and persist KPIs.

- **5. Start the REST API (optional)**

```bash
python src/api.py
```

The API will be available on `http://localhost:5000` (configurable in `api.py`).

- **6. Configure the scheduler (optional)**

1. Enable and configure `schedule` settings in `config/config.yaml`.  
2. Run:

```bash
python src/scheduler.py
```

The scheduler process will keep the pipeline running on the configured cadence.

---

### Power BI Integration

- Point Power BI (or another BI tool) at the PostgreSQL database configured in `config.yaml`.
- Use the provided views as modeling‑friendly sources:
  - `vw_sales_summary`
  - `vw_kpi_dashboard`
  - `vw_data_quality_dashboard`
  - `vw_error_log`
- Additional example queries for custom visuals are in `sql/queries,sql`.

---

### Extensibility

- **New data sources**: Add entries under `data_sources` in `config.yaml` and extend `DataIngestion`.
- **New KPIs**: Implement logic in `KPICalculator` and they will automatically flow into `fact_kpis` and the KPI API.
- **Additional alerts**: Plug into `EmailAlertSystem` to send custom notifications.
- **Different databases**: `DatabaseManager` supports PostgreSQL and SQL Server (via `mssql` + `pyodbc`) with the appropriate connection string.


