import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
from data_quality import DataQualityFramework

DB_PATH = "nectar_iot.db"

def run_pipeline(assets_csv, telemetry_csv, events_csv, db_path=DB_PATH):
    print("Starting Nectar Data Pipeline...")
    
    # 1. Run Data Quality Checks
    dq = DataQualityFramework(assets_csv, telemetry_csv, events_csv)
    dq_report = dq.run_checks()
    dq.save_report()
    
    # 2. Ingest Data
    df_assets = pd.read_csv(assets_csv)
    df_telemetry = pd.read_csv(telemetry_csv)
    df_events = pd.read_csv(events_csv)
    
    # 3. Clean Assets
    # Deduplicate assets
    df_assets_clean = df_assets.drop_duplicates(subset=["asset_id"]).copy()
    # Replace empty string or nan in hierarchy with None
    df_assets_clean["site_id"] = df_assets_clean["site_id"].replace({np.nan: None, "": None})
    df_assets_clean["building_id"] = df_assets_clean["building_id"].replace({np.nan: None, "": None})
    df_assets_clean["parent_asset_id"] = df_assets_clean["parent_asset_id"].replace({np.nan: None, "": None})
    
    valid_assets_list = df_assets_clean["asset_id"].tolist()
    
    # 4. Clean Telemetry
    # Deduplicate
    df_telemetry_clean = df_telemetry.drop_duplicates().copy()
    # Filter invalid asset IDs
    df_telemetry_clean = df_telemetry_clean[df_telemetry_clean["asset_id"].isin(valid_assets_list)]
    # Parse timestamp and drop invalid
    df_telemetry_clean["parsed_timestamp"] = pd.to_datetime(df_telemetry_clean["timestamp"], errors='coerce')
    df_telemetry_clean = df_telemetry_clean.dropna(subset=["parsed_timestamp"])
    # Drop temp/power outliers
    df_telemetry_clean["temperature"] = pd.to_numeric(df_telemetry_clean["temperature"], errors='coerce')
    df_telemetry_clean["power_consumption"] = pd.to_numeric(df_telemetry_clean["power_consumption"], errors='coerce')
    df_telemetry_clean = df_telemetry_clean[
        (df_telemetry_clean["temperature"] >= -50) & (df_telemetry_clean["temperature"] <= 100) &
        (df_telemetry_clean["power_consumption"] >= 0) & (df_telemetry_clean["power_consumption"] <= 2000)
    ]
    # Re-format timestamp to standard ISO format string for consistency
    df_telemetry_clean["timestamp"] = df_telemetry_clean["parsed_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # 5. Clean Events
    df_events_clean = df_events.drop_duplicates().copy()
    df_events_clean = df_events_clean[df_events_clean["asset_id"].isin(valid_assets_list)]
    df_events_clean["parsed_timestamp"] = pd.to_datetime(df_events_clean["timestamp"], errors='coerce')
    df_events_clean = df_events_clean.dropna(subset=["parsed_timestamp"])
    df_events_clean["timestamp"] = df_events_clean["parsed_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # 6. Generate Time Dimension
    # Gather all unique timestamps from telemetry and events
    all_timestamps = pd.concat([
        df_telemetry_clean["parsed_timestamp"],
        df_events_clean["parsed_timestamp"]
    ]).unique()
    
    df_time = pd.DataFrame({"parsed_timestamp": all_timestamps})
    df_time["time_id"] = df_time["parsed_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df_time["hour"] = df_time["parsed_timestamp"].dt.hour
    df_time["day"] = df_time["parsed_timestamp"].dt.day
    df_time["day_of_week"] = df_time["parsed_timestamp"].dt.dayofweek
    df_time["week"] = df_time["parsed_timestamp"].dt.isocalendar().week
    df_time["month"] = df_time["parsed_timestamp"].dt.month
    df_time["year"] = df_time["parsed_timestamp"].dt.year
    df_time["is_weekend"] = df_time["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    df_time_clean = df_time.drop(columns=["parsed_timestamp"]).drop_duplicates(subset=["time_id"])
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    
    # 7. Load Dimensions
    # Generate dim_site and dim_building dynamically from assets
    sites = df_assets_clean[["site_id"]].dropna().drop_duplicates()
    sites["site_name"] = sites["site_id"].apply(lambda x: x.replace("SITE_", "Site "))
    
    buildings = df_assets_clean[["building_id", "site_id"]].dropna().drop_duplicates()
    buildings["building_name"] = buildings["building_id"].apply(lambda x: x.replace("BLDG_", "Building "))
    
    # Clear existing data to avoid PK conflicts on re-runs
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    for tbl in ["fact_telemetry", "fact_energy", "fact_event", "dim_asset", "dim_building", "dim_site", "dim_time"]:
        cursor.execute(f"DELETE FROM {tbl};")
    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Load into SQL
    sites.to_sql("dim_site", conn, if_exists="append", index=False)
    buildings.to_sql("dim_building", conn, if_exists="append", index=False)
    
    df_assets_sql = df_assets_clean.copy()
    df_assets_sql.to_sql("dim_asset", conn, if_exists="append", index=False)
    df_time_clean.to_sql("dim_time", conn, if_exists="append", index=False)
    
    # 8. Load Facts
    # fact_telemetry
    df_fact_telemetry = df_telemetry_clean[[
        "timestamp", "site_id", "building_id", "asset_id", "sensor_id",
        "temperature", "humidity", "pressure", "vibration", "operating_mode"
    ]].copy()
    df_fact_telemetry.to_sql("fact_telemetry", conn, if_exists="append", index=False)
    
    # fact_energy
    df_fact_energy = df_telemetry_clean[[
        "timestamp", "site_id", "building_id", "asset_id", "power_consumption"
    ]].copy()
    df_fact_energy.to_sql("fact_energy", conn, if_exists="append", index=False)
    
    # fact_event
    df_fact_event = df_events_clean[[
        "event_id", "timestamp", "asset_id", "event_type", "severity", "message"
    ]].copy()
    df_fact_event.to_sql("fact_event", conn, if_exists="append", index=False)
    
    print("Dimensions and Facts loaded successfully!")
    
    # 9. Gold Layer / Aggregations
    # Compute Aggregations using SQL/Pandas and save to dedicated SQLite tables
    
    # A. Hourly Energy Consumption (sum of power consumption over hour per asset)
    # Since we have 15-minute readings, sum(power) * 0.25 (since power is kW and 15 mins is 0.25h) represents kWh.
    # Let's do simple sum or average. Let's compute average kW and total kWh.
    # We'll calculate: energy_kwh = sum(power_consumption) * 0.25
    df_telemetry_clean["hour_timestamp"] = df_telemetry_clean["parsed_timestamp"].dt.strftime("%Y-%m-%d %H:00:00")
    hourly_energy = df_telemetry_clean.groupby(["hour_timestamp", "site_id", "building_id", "asset_id"]).agg(
        avg_power=("power_consumption", "mean"),
        energy_kwh=("power_consumption", lambda x: sum(x) * 0.25)
    ).reset_index()
    hourly_energy.rename(columns={"hour_timestamp": "timestamp"}, inplace=True)
    hourly_energy.to_sql("agg_hourly_energy", conn, if_exists="replace", index=False)
    
    # B. Daily Asset Utilization
    # Count of "NORMAL" operating mode divided by total records for that asset per day
    df_telemetry_clean["date"] = df_telemetry_clean["parsed_timestamp"].dt.strftime("%Y-%m-%d")
    daily_util = df_telemetry_clean.groupby(["date", "site_id", "building_id", "asset_id"]).agg(
        total_readings=("operating_mode", "count"),
        normal_readings=("operating_mode", lambda x: sum(x == "NORMAL"))
    ).reset_index()
    daily_util["utilization_rate"] = daily_util["normal_readings"] / daily_util["total_readings"]
    daily_util.to_sql("agg_daily_asset_utilization", conn, if_exists="replace", index=False)
    
    # C. Average Environmental Conditions (daily average temp, humidity, pressure, vibration per asset)
    env_conds = df_telemetry_clean.groupby(["date", "site_id", "building_id", "asset_id"]).agg(
        avg_temperature=("temperature", "mean"),
        avg_humidity=("humidity", "mean"),
        avg_pressure=("pressure", "mean"),
        avg_vibration=("vibration", "mean")
    ).reset_index()
    env_conds.to_sql("agg_daily_environmental_conditions", conn, if_exists="replace", index=False)
    
    # D. Fault Statistics per Asset (daily count of events by type and severity)
    df_events_clean["date"] = df_events_clean["parsed_timestamp"].dt.strftime("%Y-%m-%d")
    fault_stats = df_events_clean.groupby(["date", "asset_id"]).agg(
        total_events=("event_id", "count"),
        num_alarms=("event_type", lambda x: sum(x == "Alarm")),
        num_warnings=("event_type", lambda x: sum(x == "Warning")),
        num_faults=("event_type", lambda x: sum(x == "Fault")),
        num_high_severity=("severity", lambda x: sum(x == "High"))
    ).reset_index()
    fault_stats.to_sql("agg_daily_fault_statistics", conn, if_exists="replace", index=False)
    
    # E. Site-level metrics, Building-level metrics, Asset-level metrics (daily)
    # Join with asset metadata to get proper building and site references for faults
    df_events_with_meta = df_events_clean.merge(df_assets_clean, on="asset_id", how="left")
    
    # Site level daily
    site_energy = df_telemetry_clean.groupby(["date", "site_id"])["power_consumption"].sum() * 0.25
    site_temp = df_telemetry_clean.groupby(["date", "site_id"])["temperature"].mean()
    site_faults = df_events_with_meta.groupby(["date", "site_id"])["event_id"].count()
    
    site_metrics = pd.DataFrame({
        "total_energy_kwh": site_energy,
        "avg_temperature": site_temp,
        "total_faults": site_faults
    }).reset_index().fillna(0)
    site_metrics.to_sql("agg_site_metrics", conn, if_exists="replace", index=False)
    
    # Building level daily
    bldg_energy = df_telemetry_clean.groupby(["date", "building_id"])["power_consumption"].sum() * 0.25
    bldg_temp = df_telemetry_clean.groupby(["date", "building_id"])["temperature"].mean()
    bldg_faults = df_events_with_meta.groupby(["date", "building_id"])["event_id"].count()
    
    bldg_metrics = pd.DataFrame({
        "total_energy_kwh": bldg_energy,
        "avg_temperature": bldg_temp,
        "total_faults": bldg_faults
    }).reset_index().fillna(0)
    bldg_metrics.to_sql("agg_building_metrics", conn, if_exists="replace", index=False)
    
    # Asset level daily
    asset_energy = df_telemetry_clean.groupby(["date", "asset_id"])["power_consumption"].sum() * 0.25
    asset_temp = df_telemetry_clean.groupby(["date", "asset_id"])["temperature"].mean()
    asset_faults = df_events_clean.groupby(["date", "asset_id"])["event_id"].count()
    
    asset_metrics = pd.DataFrame({
        "total_energy_kwh": asset_energy,
        "avg_temperature": asset_temp,
        "total_faults": asset_faults
    }).reset_index().fillna(0)
    asset_metrics.to_sql("agg_asset_metrics", conn, if_exists="replace", index=False)
    
    conn.commit()
    conn.close()
    print("Gold Layer aggregations created successfully!")
    print("Nectar Data Pipeline execution completed successfully!")

if __name__ == "__main__":
    run_pipeline("data/assets_metadata.csv", "data/telemetry_raw.csv", "data/events_raw.csv")
