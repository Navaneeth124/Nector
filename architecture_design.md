# Nectar Data Engineer Challenge - Data Architecture Design

## 1. System Architecture

Below is the proposed high-level system architecture designed to ingest, process, store, and serve high-volume IoT telemetry and event data from thousands of devices across multiple sites.

```mermaid
graph TD
    subgraph "Ingestion Layer"
        A1[IoT Temperature Sensors] -->|MQTT| B[AWS IoT Core / MQTT Broker]
        A2[Power/Energy Sensors] -->|MQTT| B
        A3[Vibration/Pressure Sensors] -->|MQTT| B
        A4[Asset Operational Events] -->|HTTP / MQTT| B
        B -->|Message Streams| C[Apache Kafka / AWS Kinesis]
    end

    subgraph "Processing Layer (Medallion Architecture)"
        C -->|Raw Stream| D[Spark Structured Streaming / Flink]
        D -->|Bronze: Append Raw Data| E[(Delta Lake / AWS S3)]
        
        %% Batch / Micro-batch
        E -->|Validation & Deduplication| F[Data Quality Framework / Great Expectations]
        F -->|Silver: Cleaned & Validated| G[(Delta Lake / Silver Storage)]
        
        %% Transformations & Aggregations
        G -->|dbt Transformations| H[Spark Batch / Databricks]
        H -->|Gold: Aggregated Metrics & Facts| I[(Snowflake / BigQuery Warehouse)]
    end

    subgraph "Storage & Modeling Layer"
        I -->|Analytical Stars & Snowflakes| J[Data Models]
        J -->|Telemetry & Energy Facts| J1[Fact Tables]
        J -->|Asset/Site/Time Dimensions| J2[Dimension Tables]
        
        %% Graph hierarchy storage
        K[(PostgreSQL / Neo4j)] <-->|Asset Hierarchical Tree| L[Hierarchy & Impact Analysis]
    end

    subgraph "Serving & Consumption Layer"
        J1 & J2 -->|SQL Queries| M[FastAPI Layer]
        K & L -->|Graph API Traversals| M
        M -->|REST APIs / GraphQL| N[Downstream Dashboards: Streamlit / PowerBI]
        M -->|Feature Engineering| O[ML / AI Training Pipelines]
    end
    
    style A1 fill:#f9f,stroke:#333,stroke-width:2px
    style A2 fill:#f9f,stroke:#333,stroke-width:2px
    style A3 fill:#f9f,stroke:#333,stroke-width:2px
    style A4 fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style J fill:#bfb,stroke:#333,stroke-width:2px
    style K fill:#bfb,stroke:#333,stroke-width:2px
    style N fill:#fbb,stroke:#333,stroke-width:2px
    style O fill:#fbb,stroke:#333,stroke-width:2px
```

### Component Selection Rationale
1. **AWS IoT Core & Apache Kafka:**
   * Provides lightweight, scalable, and secure connectivity for thousands of IoT devices via MQTT. Kafka buffers high-throughput message streams, decoupling ingestion from downstream storage and processing.
2. **Medallion Architecture (Bronze -> Silver -> Gold):**
   * **Bronze (Raw):** Preserves historical raw telemetry (fault-tolerant, reproducible pipelines).
   * **Silver (Cleaned):** Filters missing values, duplicates, and performs schema validation.
   * **Gold (Business Level):** Holds aggregated facts (hourly, daily metrics) ready for dashboards and analytics.
3. **Delta Lake & Apache Spark:**
   * Enables ACID transactions on object storage (S3/ADLS), schema enforcement, time travel, and high-performance querying. Spark handles massive parallel ingestion and batch transformations.
4. **Snowflake or Google BigQuery:**
   * Serverless, fully managed MPP data warehouses optimized for analytical queries (dashboarding, ad-hoc BI, historical reporting).
5. **Neo4j or PostgreSQL (for Hierarchy):**
   * Hierarchical connections (e.g. Site -> Building -> Chiller -> AHU) are highly recursive. A graph-based schema or a relational database with recursive CTEs (Common Table Expressions) allows flexible parent-child querying and downstream impact analysis.

---

## 2. Analytical Data Model (ER Diagram)

To support dashboarding, historical reporting, and ML workloads, we design a star-like analytical schema.

```mermaid
erDiagram
    dim_site {
        VARCHAR site_id PK
        VARCHAR site_name
        VARCHAR country
        VARCHAR timezone
    }
    dim_building {
        VARCHAR building_id PK
        VARCHAR building_name
        VARCHAR site_id FK
    }
    dim_asset {
        VARCHAR asset_id PK
        VARCHAR asset_name
        VARCHAR asset_type
        VARCHAR manufacturer
        DATE installation_date
        VARCHAR building_id FK
        VARCHAR parent_asset_id FK
    }
    dim_time {
        TIMESTAMP time_id PK
        INTEGER hour
        INTEGER day
        INTEGER day_of_week
        INTEGER week
        INTEGER month
        INTEGER year
        VARCHAR is_weekend
    }
    fact_telemetry {
        BIGINT telemetry_id PK
        TIMESTAMP timestamp FK
        VARCHAR asset_id FK
        VARCHAR sensor_id
        FLOAT temperature
        FLOAT humidity
        FLOAT pressure
        FLOAT vibration
        VARCHAR operating_mode
    }
    fact_energy {
        BIGINT energy_id PK
        TIMESTAMP timestamp FK
        VARCHAR asset_id FK
        FLOAT power_consumption
    }
    fact_event {
        VARCHAR event_id PK
        TIMESTAMP timestamp FK
        VARCHAR asset_id FK
        VARCHAR event_type
        VARCHAR severity
        VARCHAR message
    }

    dim_site ||--o{ dim_building : "contains"
    dim_building ||--o{ dim_asset : "houses"
    dim_asset ||--o{ dim_asset : "parent-of (hierarchy)"
    
    dim_asset ||--o{ fact_telemetry : "generates"
    dim_asset ||--o{ fact_energy : "consumes"
    dim_asset ||--o{ fact_event : "triggers"
    
    dim_time ||--o{ fact_telemetry : "logs"
    dim_time ||--o{ fact_energy : "logs"
    dim_time ||--o{ fact_event : "logs"
```

### Partitioning Strategy
- **`fact_telemetry` and `fact_energy`:** Partitioned by `timestamp` (daily or monthly depending on volume) and sub-partitioned by `site_id` (or `site_id` included in clustering key). This ensures queries focusing on specific sites or timeframes prune unnecessary partitions.
- **`dim_time`:** Populated statically or dynamically, acts as a shared lookup table.

### Indexing Strategy
- Primary Keys (`PK`) and Foreign Keys (`FK`) are indexed automatically in most warehouses or relational engines (like Postgres/SQLite).
- Composite indexes on `(asset_id, timestamp)` for facts are crucial for time-series range queries (e.g. fetching last 24h telemetry for a specific chiller).

---

## 3. Design Assumptions
- Telemetry measurements occur regularly (e.g. every 15 minutes).
- Energy consumption is represented as a continuous cumulative/differential reading (kW or kWh).
- Missing values in sensor readings can be filled or flagged (our pipeline flags them in the quality report but loads them or handles them according to specific business rules).
- Disconnected assets are nodes present in the Asset registry but completely lacking any connections or active telemetry reporting.
