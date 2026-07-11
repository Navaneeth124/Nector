# Project Presentation Report
## Nectar IoT Data Platform Implementation

---

### Page 1: Executive Summary and Project Objectives

#### Context
Nectar's smart building platform receives telemetry and event data from thousands of IoT devices deployed across multiple customer sites. To extract business value, dashboard metrics, and enable machine learning pipelines, a reliable, structured data engineering platform is required.

#### Objectives
1. **Design a Scalable Data Pipeline:** Architect an ingestion, validation, and loading pipeline following a medallion pattern (Bronze -> Silver -> Gold).
2. **Implement Data Validation & Quality Checks:** Automate checking for nulls, duplicates, invalid IDs, outliers, and late-arriving telemetry logs.
3. **Model the Analytical Database:** Design fact and dimension tables optimized for high-performance window-function queries.
4. **Model Asset Hierarchy:** Handle complex parent-child relations (e.g. Chillers -> AHUs -> sensors) to perform downstream impact analysis.
5. **Establish Pipeline Orchestration:** Design scheduling, retries, failure handlers, and alerting mechanisms for production runs.

---

### Page 2: Ingestion and Data Quality Framework

#### Ingestion Strategy
Raw data files (`assets_metadata.csv`, `telemetry_raw.csv`, `events_raw.csv`) are ingested by the pipeline. In production, this maps to files landed in cloud object storage (e.g. Amazon S3 or Azure ADLS) from message brokers.

#### Data Quality Rules
We implement a dedicated validation class (`DataQualityFramework`) which runs the following rules before loading the database:
- **Referential Integrity:** Verifies that telemetry and events reference valid asset IDs present in the asset metadata registry.
- **Completeness Checks:** Identifies missing mandatory fields (nulls).
- **Uniqueness Checks:** Identifies and flags duplicate records.
- **Outlier Boundary Checks:** Flags telemetry values outside normal operational ranges (e.g. Temperature < -50 or > 100 °C; Power consumption > 2000 kW).
- **Late-Arriving Log Detection:** Identifies telemetry timestamps that are delayed by more than 24 hours relative to the maximum ingestion timestamp in the current batch.

All validation anomalies are recorded in a JSON data quality report file (`data/data_quality_report.json`) to maintain a complete operational audit trail.

---

### Page 3: Data Modeling and Schema Design

The data platform uses a Star Schema analytical data model, separating descriptive attributes (Dimensions) from numeric metrics (Facts) to maximize query performance.

#### Dimensions
- **`dim_site`:** Site identifiers and metadata.
- **`dim_building`:** Buildings associated with sites.
- **`dim_asset`:** Assets mapping types (Chiller, AHU, Pump, Fan), manufacturer, installation dates, and containing a self-referencing `parent_asset_id` to establish structural hierarchy.
- **`dim_time`:** Granular time dimensional parameters (hour, day, week, month, year, day of week, weekend flags) to avoid complex date arithmetic in queries.

#### Facts
- **`fact_telemetry`:** Time-series of sensor measurements (temperature, humidity, pressure, vibration).
- **`fact_energy`:** Ingested power consumption readings (kW).
- **`fact_event`:** System alarms, warnings, and faults.

#### Physical Model Optimization
- **Partitioning:** Facts are partitioned by timestamp (monthly or daily) to restrict query scanning size.
- **Indexing:** Primary keys and foreign keys are explicitly indexed. Composite indices are created on `(asset_id, timestamp)` for facts to speed up time-series range lookups.

---

### Page 4: Asset Hierarchy and Graph Topology

Asset relationships in commercial buildings are deeply nested. Relational tables struggle with recursive parent-child traversal at scale.

```
                   [ SITE A ]
                       │
                 [ Building 1 ]
                   ┌───┴───┐
             [Chiller-01] [Pump-01]
               ┌───┴───┐       │
            [AHU-01] [AHU-02] [Flow Sensor-01]
```

#### Graph representation
We model the hierarchy as a Directed Acyclic Graph (DAG) using the NetworkX library in Python. Edges are established from parent assets to dependent children (e.g. Chiller-01 -> AHU-01).

#### Traversal Operations
1. **Downstream Impact Simulation:** If Chiller-01 fails, we recursively traverse descendants to identify all dependent assets that lose cooling (AHU-01 and AHU-02).
2. **Orphan Identification:** Diagnoses assets that have been registered without site or building references (e.g. Exhaust Fan-01).
3. **Disconnected Components:** Detects isolated assets that have site and building associations but lack connection edges in the system tree.

---

### Page 5: Pipeline Operations and Orchestration

#### Orchestration via Prefect or Apache Airflow
The data pipeline is scheduled and monitored via an orchestrator:
- **Task Dependencies:** Upstream extraction tasks land raw files -> data quality checks run -> if validated, loading tasks refresh facts and dimensions -> gold aggregations update.
- **Failure Recovery:** Retries are set with exponential backoff on ingestion interfaces (e.g., 3 retries, 5-minute delays) to resolve temporary network dropouts.
- **Quarantine Management:** Telemetry batches with severe schema mismatches are diverted to a quarantine repository for investigation, preventing database pollution.
- **Proactive Alerting:** Hook listeners (`on_failure` triggers) dispatch notifications to Slack or PagerDuty with execution states, logs, and failure details.
