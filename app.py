import streamlit as st
import sqlite3
import pandas as pd
import json
import os
import networkx as nx
from src.asset_graph import AssetHierarchyGraph

# Set page config for a premium look
st.set_page_config(
    page_title="Nectar IoT Analytics & Data Platform",
    page_icon="chart",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark mode styling injection
st.markdown("""
<style>
    .reportview-container {
        background-color: #0f1116;
    }
    .metric-card {
        background-color: #1a1f2c;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #2d3748;
    }
    .highlight-box {
        background-color: #1e1e24;
        border-left: 5px solid #ff4b4b;
        padding: 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to get database connection
def get_db_connection():
    return sqlite3.connect("nectar_iot.db")

# Title and header
st.title("Nectar IoT Data Platform & Analytics")
st.markdown("An interactive dashboard showcasing the completed Data Engineer Challenge deliverables, including pipeline analysis, data quality checks, graph-based asset hierarchy, and SQL challenge executors.")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", [
    "Architecture & Design", 
    "Data Quality Report", 
    "Telemetry & Metrics", 
    "SQL Challenge Runner", 
    "Asset Graph Hierarchy"
])

# Initialize Asset Graph
if os.path.exists("nectar_iot.db"):
    hierarchy = AssetHierarchyGraph()
else:
    hierarchy = None

# ================= PAGE 1: ARCHITECTURE & DESIGN =================
if page == "Architecture & Design":
    st.header("System Architecture & Data Model")
    
    st.subheader("High-Level Medallion Architecture")
    st.markdown("""
    This project is built using a modern time-series and analytical pipeline architecture. 
    1. **Ingestion Layer:** Real-time sensor readings and event streams are captured and buffered in message queues (e.g. Apache Kafka or AWS Kinesis).
    2. **Bronze Layer (Raw Storage):** Unvalidated CSV/JSON formats stored directly on Object Storage (S3/ADLS).
    3. **Silver Layer (Cleaned & Validated):** Data validated using a Python/Pandas data quality framework to detect missing values, duplicates, out-of-bounds outliers, and late-arriving logs.
    4. **Gold Layer (Aggregated Analytical Warehouses):** Formatted into a Star Schema with Facts and Dimensions in SQLite/Snowflake. Dedicated analytical aggregates are built hourly/daily for fast dashboard rendering.
    """)
    
    st.subheader("Data Models & ER Schema")
    st.markdown("""
    The database uses a classic **Star Schema** optimized for analytical queries:
    - **Dimensions:** 
        - `dim_site`: Site configuration.
        - `dim_building`: Buildings nested under sites.
        - `dim_asset`: Equipment and sensors, containing a self-referencing `parent_asset_id` to form hierarchical dependency trees.
        - `dim_time`: Dynamic time attributes for time-series parsing.
    - **Facts:**
        - `fact_telemetry`: Temperature, humidity, pressure, and vibration time series.
        - `fact_energy`: Real-time power consumption metrics.
        - `fact_event`: Operational events, alarms, and faults triggered by assets.
    """)
    
    # Render ER Diagram using Mermaid
    st.subheader("Mermaid ER Diagram")
    st.code("""
    dim_site ||--o{ dim_building : contains
    dim_building ||--o{ dim_asset : houses
    dim_asset ||--o{ dim_asset : parent-of (hierarchy)
    dim_asset ||--o{ fact_telemetry : generates
    dim_asset ||--o{ fact_energy : consumes
    dim_asset ||--o{ fact_event : triggers
    """, language="mermaid")

# ================= PAGE 2: DATA QUALITY REPORT =================
elif page == "Data Quality Report":
    st.header("Data Quality Validation Framework")
    st.markdown("Results from the validation pipeline run (`data/data_quality_report.json`).")
    
    report_path = "data/data_quality_report.json"
    if not os.path.exists(report_path):
        st.error("Data Quality Report not found! Please run the pipeline script first.")
    else:
        with open(report_path, "r") as f:
            report_data = json.load(f)
            
        st.info(f"Report Generated At: {report_data['execution_time']}")
        
        # Ingestion Metrics Cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Telemetry Ingested", report_data["summary"]["telemetry"]["total_records"])
            st.metric("Telemetry Duplicates", report_data["summary"]["telemetry"]["duplicates"])
        with col2:
            st.metric("Total Events Ingested", report_data["summary"]["events"]["total_records"])
            st.metric("Event Duplicates", report_data["summary"]["events"]["duplicates"])
        with col3:
            st.metric("Total Assets Registered", report_data["summary"]["assets"]["total_records"])
            st.metric("Asset Duplicates", report_data["summary"]["assets"]["duplicates"])
            
        st.subheader("Telemetry Anomalies & Validation Failures")
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            st.warning(f"Invalid Asset IDs: {report_data['summary']['telemetry']['invalid_asset_ids_count']}")
        with col_t2:
            st.warning(f"Invalid Timestamps: {report_data['summary']['telemetry']['invalid_timestamps_count']}")
        with col_t3:
            st.warning(f"Outlier Readings: {report_data['summary']['telemetry']['temp_outliers_count'] + report_data['summary']['telemetry']['power_outliers_count']}")
        with col_t4:
            st.warning(f"Late-Arriving Logs: {report_data['summary']['telemetry']['late_arriving_count']}")
            
        # Detailed samples
        with st.expander("Show Anomaly Details"):
            st.write("### Invalid Asset IDs Found in Telemetry")
            st.write(report_data["details"]["telemetry"]["invalid_asset_ids"])
            
            st.write("### Outlier Temperature Readings (Sample)")
            if report_data["details"]["telemetry"]["outlier_temp_samples"]:
                st.table(pd.DataFrame(report_data["details"]["telemetry"]["outlier_temp_samples"]))
            else:
                st.write("No temperature outliers found.")
                
            st.write("### Outlier Power Consumption Readings (Sample)")
            if report_data["details"]["telemetry"]["outlier_power_samples"]:
                st.table(pd.DataFrame(report_data["details"]["telemetry"]["outlier_power_samples"]))
            else:
                st.write("No power consumption outliers found.")
                
            st.write("### Late-Arriving Telemetry Samples")
            if report_data["details"]["telemetry"]["late_arriving_samples"]:
                st.table(pd.DataFrame(report_data["details"]["telemetry"]["late_arriving_samples"]))
            else:
                st.write("No late arriving data found.")

# ================= PAGE 3: TELEMETRY & METRICS =================
elif page == "Telemetry & Metrics":
    st.header("Historical Telemetry & Aggregated Metrics")
    
    if not os.path.exists("nectar_iot.db"):
        st.error("SQLite database not found! Please run the pipeline script first.")
    else:
        conn = get_db_connection()
        
        # Dropdowns
        sites_df = pd.read_sql("SELECT site_id FROM dim_site", conn)
        site_list = sites_df["site_id"].tolist()
        selected_site = st.selectbox("Select Site:", site_list)
        
        assets_df = pd.read_sql(f"SELECT asset_id, asset_name FROM dim_asset WHERE site_id = '{selected_site}'", conn)
        asset_list = assets_df["asset_id"].tolist()
        selected_asset = st.selectbox("Select Asset to View History:", asset_list)
        
        # Load daily metrics for selected asset
        df_asset_daily = pd.read_sql(f"""
            SELECT date, total_energy_kwh, avg_temperature, total_faults
            FROM agg_asset_metrics
            WHERE asset_id = '{selected_asset}'
            ORDER BY date
        """, conn)
        
        col_m1, col_m2, col_m3 = st.columns(3)
        if not df_asset_daily.empty:
            with col_m1:
                st.metric("Total Daily Energy (kWh)", f"{df_asset_daily['total_energy_kwh'].sum():.2f}")
            with col_m2:
                st.metric("Average Temperature (°C)", f"{df_asset_daily['avg_temperature'].mean():.2f}")
            with col_m3:
                st.metric("Total faults logged", int(df_asset_daily['total_faults'].sum()))
                
        # Time-series plotting
        st.subheader("Sensor Time Series (Cleaned facts)")
        df_fact_telemetry = pd.read_sql(f"""
            SELECT timestamp, temperature, humidity, pressure, vibration
            FROM fact_telemetry
            WHERE asset_id = '{selected_asset}'
            ORDER BY timestamp
        """, conn)
        
        if not df_fact_telemetry.empty:
            df_fact_telemetry['timestamp'] = pd.to_datetime(df_fact_telemetry['timestamp'])
            df_fact_telemetry.set_index('timestamp', inplace=True)
            
            # Select column
            metric_to_plot = st.selectbox("Select Metric to Plot:", ["temperature", "humidity", "pressure", "vibration"])
            st.line_chart(df_fact_telemetry[[metric_to_plot]])
        else:
            st.write("No telemetry logs found for this asset.")
            
        conn.close()

# ================= PAGE 4: SQL CHALLENGE RUNNER =================
elif page == "SQL Challenge Runner":
    st.header("SQL Challenge Live Queries")
    st.markdown("Execute the SQL challenge questions directly against the loaded SQLite database `nectar_iot.db`.")
    
    questions = [
        "1. Top 10 assets with the highest energy consumption",
        "2. Average daily energy consumption for each site",
        "3. Assets that generated more than 10 faults in the last 30 days",
        "4. Find assets that have not reported telemetry for the last 24 hours",
        "5. Calculate hourly utilization for each building",
        "6. Identify sites with abnormal increases in power consumption (>50% YoY/DoD)"
    ]
    
    queries = [
        # Query 1
        """SELECT 
    fe.asset_id,
    da.asset_name,
    da.asset_type,
    da.site_id,
    ROUND(SUM(fe.power_consumption) * 0.25, 2) as total_energy_kwh
FROM fact_energy fe
JOIN dim_asset da ON fe.asset_id = da.asset_id
GROUP BY fe.asset_id, da.asset_name, da.asset_type, da.site_id
ORDER BY total_energy_kwh DESC
LIMIT 10;""",
        # Query 2
        """WITH daily_site_energy AS (
    SELECT 
        site_id,
        DATE(timestamp) as date_val,
        SUM(power_consumption) * 0.25 as daily_energy
    FROM fact_energy
    WHERE site_id IS NOT NULL AND site_id != ''
    GROUP BY site_id, DATE(timestamp)
)
SELECT 
    site_id,
    ROUND(AVG(daily_energy), 2) as avg_daily_energy_kwh
FROM daily_site_energy
GROUP BY site_id;""",
        # Query 3
        """SELECT 
    fe.asset_id,
    da.asset_name,
    da.asset_type,
    COUNT(fe.event_id) as fault_count
FROM fact_event fe
JOIN dim_asset da ON fe.asset_id = da.asset_id
WHERE fe.event_type = 'Fault'
  AND datetime(fe.timestamp) >= datetime('now', '-30 days')
GROUP BY fe.asset_id, da.asset_name, da.asset_type
HAVING fault_count > 10;""",
        # Query 4
        """WITH max_db_time AS (
    SELECT MAX(timestamp) as max_time FROM fact_telemetry
)
SELECT 
    da.asset_id,
    da.asset_name,
    da.asset_type,
    da.site_id,
    MAX(ft.timestamp) as last_reported_time
FROM dim_asset da
LEFT JOIN fact_telemetry ft ON da.asset_id = ft.asset_id
CROSS JOIN max_db_time mdt
GROUP BY da.asset_id, da.asset_name, da.asset_type, da.site_id
HAVING last_reported_time IS NULL 
   OR datetime(last_reported_time) < datetime(mdt.max_time, '-24 hours');""",
        # Query 5
        """SELECT 
    building_id,
    strftime('%Y-%m-%d %H:00:00', timestamp) as hour_timestamp,
    COUNT(CASE WHEN operating_mode = 'NORMAL' THEN 1 END) as normal_readings,
    COUNT(*) as total_readings,
    ROUND(COUNT(CASE WHEN operating_mode = 'NORMAL' THEN 1 END) * 100.0 / COUNT(*), 2) as utilization_percentage
FROM fact_telemetry
WHERE building_id IS NOT NULL AND building_id != ''
GROUP BY building_id, hour_timestamp
ORDER BY building_id, hour_timestamp
LIMIT 15;""",
        # Query 6
        """WITH daily_site_energy AS (
    SELECT 
        site_id,
        DATE(timestamp) as date_val,
        SUM(power_consumption) * 0.25 as total_energy
    FROM fact_energy
    WHERE site_id IS NOT NULL AND site_id != ''
    GROUP BY site_id, DATE(timestamp)
),
energy_growth AS (
    SELECT 
        site_id,
        date_val,
        total_energy,
        LAG(total_energy) OVER (PARTITION BY site_id ORDER BY date_val) as prev_day_energy
    FROM daily_site_energy
)
SELECT 
    site_id,
    date_val as detection_date,
    ROUND(prev_day_energy, 2) as previous_day_energy_kwh,
    ROUND(total_energy, 2) as current_day_energy_kwh,
    ROUND(((total_energy - prev_day_energy) / prev_day_energy) * 100.0, 2) as percentage_increase
FROM energy_growth
WHERE prev_day_energy IS NOT NULL AND prev_day_energy > 0
  AND total_energy > prev_day_energy * 1.5;"""
    ]
    
    selected_query_index = st.selectbox("Select SQL Query:", range(len(questions)), format_func=lambda x: questions[x])
    
    st.write("### SQL Statement")
    st.code(queries[selected_query_index], language="sql")
    
    if st.button("Execute Query"):
        if not os.path.exists("nectar_iot.db"):
            st.error("Database does not exist! Please run the pipeline script first.")
        else:
            conn = get_db_connection()
            try:
                df = pd.read_sql_query(queries[selected_query_index], conn)
                st.write("### Query Result")
                if df.empty:
                    st.warning("Query returned an empty dataset.")
                else:
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Execution Error: {e}")
            finally:
                conn.close()

# ================= PAGE 5: ASSET GRAPH HIERARCHY =================
elif page == "Asset Graph Hierarchy":
    st.header("Asset Hierarchy & Topology Graph")
    st.markdown("Query hierarchical relationships between sites, buildings, chillers, AHUs, pumps, and sensors using **NetworkX** directed graphs.")
    
    if hierarchy is None:
        st.error("Hierarchy graph could not be loaded. Ensure the database is initialized.")
    else:
        tab1, tab2, tab3 = st.tabs(["Search Asset Hierarchy", "Impact & Connectivity Diagnostics", "Raw Asset Graph Nodes"])
        
        with tab1:
            st.subheader("Asset Details Explorer")
            all_asset_ids = list(hierarchy.graph.nodes)
            selected_node = st.selectbox("Select Asset to Query:", all_asset_ids)
            
            # Show details of selected node
            data = hierarchy.graph.nodes[selected_node]
            st.write(f"**Asset Name:** {data.get('name')}")
            st.write(f"**Type:** {data.get('type')}")
            st.write(f"**Manufacturer:** {data.get('manufacturer')}")
            st.write(f"**Site:** {data.get('site_id')}")
            st.write(f"**Building:** {data.get('building_id')}")
            
            # Query parent/child
            parent, children = hierarchy.get_parent_and_children(selected_node)
            
            col_p, col_c = st.columns(2)
            with col_p:
                st.markdown("#### Direct Parent Asset")
                if parent:
                    p_data = hierarchy.graph.nodes[parent]
                    st.success(f"{parent} ({p_data.get('name')})")
                else:
                    st.write("No parent asset (Top-level asset)")
            with col_c:
                st.markdown("#### Direct Children Assets")
                if children:
                    for child in children:
                        c_data = hierarchy.graph.nodes[child]
                        st.info(f"{child} ({c_data.get('name')}) - Type: {c_data.get('type')}")
                else:
                    st.write("No child assets (Leaf node)")
                    
        with tab2:
            st.subheader("Downstream Impact Analysis")
            st.markdown("Simulate the failure of a parent asset to find all downstream dependent assets impacted.")
            
            impact_asset = st.selectbox("Select Asset to Simulate Failure:", all_asset_ids, key="impact_select")
            impacted = hierarchy.get_downstream_impacted(impact_asset)
            
            if impacted:
                st.error(f"FAILED NODE: {impact_asset} ({hierarchy.graph.nodes[impact_asset].get('name')})")
                st.write("Downstream assets that will lose functionality:")
                impact_df = pd.DataFrame([
                    {
                        "Asset ID": node,
                        "Name": hierarchy.graph.nodes[node].get("name"),
                        "Type": hierarchy.graph.nodes[node].get("type")
                    } for node in impacted
                ])
                st.table(impact_df)
            else:
                st.success(f"Safe Node: {impact_asset} ({hierarchy.graph.nodes[impact_asset].get('name')}) has no downstream dependent assets.")
                
            st.subheader("Orphan & Disconnected Diagnostics")
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                st.markdown("#### Orphan Assets")
                st.markdown("*Assets lacking site_id or building_id information*")
                orphans = hierarchy.get_orphan_assets()
                if orphans:
                    st.table(pd.DataFrame(orphans, columns=["Asset ID", "Name", "Type"]))
                else:
                    st.write("No orphan assets found.")
                    
            with col_d2:
                st.markdown("#### Disconnected Assets")
                st.markdown("*Isolated assets with site/building registration but no hierarchical connections*")
                disconnected = hierarchy.get_disconnected_assets()
                if disconnected:
                    st.table(pd.DataFrame(disconnected, columns=["Asset ID", "Name", "Type"]))
                else:
                    st.write("No disconnected assets found.")
                    
        with tab3:
            st.subheader("Graph Summary Statistics")
            st.write(f"**Total Nodes (Assets):** {hierarchy.graph.number_of_nodes()}")
            st.write(f"**Total Edges (Relationships):** {hierarchy.graph.number_of_edges()}")
            
            st.subheader("Complete Asset Nodes Table")
            nodes_data = []
            for node, data in hierarchy.graph.nodes(data=True):
                nodes_data.append({
                    "asset_id": node,
                    "name": data.get("name"),
                    "type": data.get("type"),
                    "manufacturer": data.get("manufacturer"),
                    "site_id": data.get("site_id"),
                    "building_id": data.get("building_id"),
                    "parent_asset_id": data.get("parent_asset_id")
                })
            st.dataframe(pd.DataFrame(nodes_data), use_container_width=True)
