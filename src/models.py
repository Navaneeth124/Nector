import sqlite3
import os

DB_PATH = "nectar_iot.db"

def init_db(db_path=DB_PATH):
    """Initializes the SQLite database with dim and fact tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Dimension Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_site (
            site_id TEXT PRIMARY KEY,
            site_name TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_building (
            building_id TEXT PRIMARY KEY,
            building_name TEXT NOT NULL,
            site_id TEXT,
            FOREIGN KEY (site_id) REFERENCES dim_site(site_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_asset (
            asset_id TEXT PRIMARY KEY,
            asset_name TEXT NOT NULL,
            asset_type TEXT,
            manufacturer TEXT,
            installation_date TEXT,
            site_id TEXT,
            building_id TEXT,
            parent_asset_id TEXT,
            FOREIGN KEY (site_id) REFERENCES dim_site(site_id),
            FOREIGN KEY (building_id) REFERENCES dim_building(building_id),
            FOREIGN KEY (parent_asset_id) REFERENCES dim_asset(asset_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_time (
            time_id TEXT PRIMARY KEY, -- Timestamp string 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
            hour INTEGER,
            day INTEGER,
            day_of_week INTEGER, -- 0-6 (Sunday is 0)
            week INTEGER,
            month INTEGER,
            year INTEGER,
            is_weekend INTEGER -- 0 or 1
        )
    """)
    
    # 2. Fact Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_telemetry (
            telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            site_id TEXT,
            building_id TEXT,
            asset_id TEXT NOT NULL,
            sensor_id TEXT,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            vibration REAL,
            operating_mode TEXT,
            FOREIGN KEY (timestamp) REFERENCES dim_time(time_id),
            FOREIGN KEY (site_id) REFERENCES dim_site(site_id),
            FOREIGN KEY (building_id) REFERENCES dim_building(building_id),
            FOREIGN KEY (asset_id) REFERENCES dim_asset(asset_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_energy (
            energy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            site_id TEXT,
            building_id TEXT,
            asset_id TEXT NOT NULL,
            power_consumption REAL,
            FOREIGN KEY (timestamp) REFERENCES dim_time(time_id),
            FOREIGN KEY (site_id) REFERENCES dim_site(site_id),
            FOREIGN KEY (building_id) REFERENCES dim_building(building_id),
            FOREIGN KEY (asset_id) REFERENCES dim_asset(asset_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_event (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            event_type TEXT,
            severity TEXT,
            message TEXT,
            FOREIGN KEY (timestamp) REFERENCES dim_time(time_id),
            FOREIGN KEY (asset_id) REFERENCES dim_asset(asset_id)
        )
    """)
    
    # 3. Create Indexes for query optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_asset_time ON fact_telemetry(asset_id, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_asset_time ON fact_energy(asset_id, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_asset_time ON fact_event(asset_id, timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_hierarchy ON dim_asset(parent_asset_id)")
    
    conn.commit()
    conn.close()
    print(f"Database initialized and schema created at '{db_path}'.")

if __name__ == "__main__":
    init_db()
