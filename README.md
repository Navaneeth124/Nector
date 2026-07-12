# Nectar Data Engineer Challenge

This repository contains the complete implementation for the Nectar Data Engineer Challenge. The solution provides a structured ingestion, validation, processing, and analytical pipeline for managing high-volume IoT telemetry and event data from connected building assets.

The solution is implemented in Python and SQLite, featuring a graph-based asset hierarchy engine built with NetworkX and an interactive management dashboard created with Streamlit.

---

## Overview

The platform uses a medallion data architecture to process and refine raw IoT telemetry and event records:

1. **Ingestion Layer:** Captures streaming data from temperature, humidity, pressure, vibration, and energy sensors.
2. **Bronze Layer (Raw Data):** Landing directory for raw CSV/JSON records directly from the field.
3. **Silver Layer (Cleaned & Validated Data):** Cleanses data by removing duplicates, verifying schema structures, applying boundary checks to filter out sensor anomalies/outliers, and matching IDs against the asset metadata registry.
4. **Gold Layer (Analytical Aggregates):** Loads structured facts and dimensions into SQLite and builds analytical aggregates optimized for business reporting, dashboards, and machine learning workloads.

---

## Project Structure

```
nector/
├── data/
│   ├── assets_metadata.csv           # Registered assets metadata
│   ├── telemetry_raw.csv             # Raw sensor logs containing errors
│   ├── events_raw.csv                # Raw events and alarms
│   └── data_quality_report.json      # Output of the validation pipeline
├── src/
│   ├── generate_data.py              # Synthetic data generator for development
│   ├── models.py                     # SQLite database schema setup
│   ├── data_quality.py               # Ingestion validation framework
│   ├── pipeline.py                   # Data Pipeline orchestrator (ETL)
│   ├── asset_graph.py                # Graph hierarchy engine
│   ├── sql_queries.sql               # Analytical SQL queries
│   └── run_queries.py                # Query verification runner
├── app.py                            # Streamlit administration dashboard
├── nectar_iot.db                     # SQLite database file
├── architecture_design.md            # Detailed system design specs
├── Nectar_Data_Platform_Demo.ipynb   # Jupyter walkthrough notebook
├── Report.md                         # Project presentation report (5 pages)
└── README.md                         # This file
```

---

## Setup and Running Instructions

### 1. Prerequisites
- Python 3.10 or higher
- `pip` package manager

### 2. Installation
Install the required libraries:
```bash
pip install pandas networkx streamlit
```

### 3. Initialize and Run the Data Pipeline
Execute the pipeline stages in order to initialize the database schema, generate mock telemetry datasets, run quality checks, and load the analytical tables:
```bash
# Set up database schema
python src/models.py

# Generate testing data with simulated sensor anomalies
python src/generate_data.py

# Run the ETL pipeline and data quality checks
python src/pipeline.py
```

### 4. Open the Jupyter Notebook
To run the interactive step-by-step walkthrough:
```bash
jupyter notebook Nectar_Data_Platform_Demo.ipynb
```

### 5. Launch the Streamlit Dashboard
To run the interactive interface for operations and reporting:
```bash
streamlit run app.py
```

---

## System Design and Trade-offs

### Assumptions
- Telemetry data is pushed in batches or streams at 15-minute intervals.
- The energy consumption field in telemetry represents instantaneous power consumption (kW). The total energy consumed (kWh) is calculated by integrating this rate over time (e.g. `power * 0.25 hours`).
- Asset relationships form a directed acyclic graph (DAG) where parents (such as Chillers or Pumps) feed children (such as Air Handling Units or flow sensors).

### Design Decisions
- **SQLite Database:** Used for the analytical model locally. It supports advanced SQL features (CTEs, Window Functions, LAG) without requiring external server setup, making it ideal for portable runs. In a production cloud setting, this would map directly to Snowflake or Google BigQuery.
- **NetworkX for Graph Traversal:** Used to model hierarchical connections. Traditional SQL databases struggle with arbitrary-depth recursive lookups; graph representations simplify queries like downstream impact analysis and isolated asset detection.
- **Great Expectations / Custom Validator Pattern:** Built a clean custom validation runner to capture anomalies and save a JSON quality audit trail before loading.

### Orchestration Design
For production scheduling, the pipeline can be scheduled using Prefect or Apache Airflow. Ingestion tasks run at scheduled intervals, triggering quality validations. Logs containing missing or malformed telemetry are written to a quarantine table for inspection, while clean runs refresh the target analytical aggregates.
