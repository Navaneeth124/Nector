import pandas as pd
import numpy as np
import json
from datetime import datetime

class DataQualityFramework:
    def __init__(self, assets_file, telemetry_file, events_file):
        self.assets_file = assets_file
        self.telemetry_file = telemetry_file
        self.events_file = events_file
        self.report = {
            "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {},
            "details": {}
        }
        
    def run_checks(self):
        # 1. Load Data
        df_assets = pd.read_csv(self.assets_file)
        df_telemetry = pd.read_csv(self.telemetry_file)
        df_events = pd.read_csv(self.events_file)
        
        valid_asset_ids = set(df_assets["asset_id"].dropna().unique())
        
        # 2. Check Assets
        assets_nulls = df_assets.isnull().sum().to_dict()
        assets_duplicates = int(df_assets.duplicated(subset=["asset_id"]).sum())
        
        self.report["summary"]["assets"] = {
            "total_records": len(df_assets),
            "duplicates": assets_duplicates,
            "missing_values": assets_nulls
        }
        
        # 3. Check Telemetry
        # Duplicates
        telemetry_duplicates = int(df_telemetry.duplicated().sum())
        
        # Null values
        telemetry_nulls = df_telemetry.isnull().sum().to_dict()
        
        # Invalid Asset IDs
        # Convert asset_id to string and strip
        telemetry_assets = df_telemetry["asset_id"].astype(str).str.strip()
        invalid_telemetry_assets = df_telemetry[~telemetry_assets.isin(valid_asset_ids)]
        invalid_asset_ids_list = invalid_telemetry_assets["asset_id"].unique().tolist()
        num_invalid_assets = len(invalid_telemetry_assets)
        
        # Invalid Timestamps
        # Try parsing timestamps, find errors
        def check_timestamps(df, col):
            parsed = pd.to_datetime(df[col], errors='coerce')
            invalid_indices = df[parsed.isna() | (df[col] == 'INVALID_TIME')].index
            return invalid_indices.tolist()
            
        invalid_telemetry_time_indices = check_timestamps(df_telemetry, "timestamp")
        num_invalid_time = len(invalid_telemetry_time_indices)
        
        # Outliers check for numeric columns
        # e.g. temperature out of [-50, 150] °C, power out of [0, 5000] kW
        df_telemetry["temp_numeric"] = pd.to_numeric(df_telemetry["temperature"], errors='coerce')
        df_telemetry["power_numeric"] = pd.to_numeric(df_telemetry["power_consumption"], errors='coerce')
        
        temp_outliers = df_telemetry[(df_telemetry["temp_numeric"] < -50) | (df_telemetry["temp_numeric"] > 100)]
        power_outliers = df_telemetry[(df_telemetry["power_numeric"] < 0) | (df_telemetry["power_numeric"] > 2000)]
        
        # Late-Arriving Data
        # Assume late-arriving is telemetry with timestamp < max_timestamp - 1 day, 
        # or compare to the median/mean processing time. Let's define it as:
        # timestamp is more than 24 hours older than the maximum timestamp in the batch.
        parsed_times = pd.to_datetime(df_telemetry["timestamp"], errors='coerce')
        max_time = parsed_times.max()
        late_arriving = df_telemetry[parsed_times < (max_time - pd.Timedelta(hours=24))]
        num_late_arriving = len(late_arriving)
        
        self.report["summary"]["telemetry"] = {
            "total_records": len(df_telemetry),
            "duplicates": telemetry_duplicates,
            "missing_values": telemetry_nulls,
            "invalid_asset_ids_count": num_invalid_assets,
            "invalid_timestamps_count": num_invalid_time,
            "temp_outliers_count": len(temp_outliers),
            "power_outliers_count": len(power_outliers),
            "late_arriving_count": num_late_arriving
        }
        
        self.report["details"]["telemetry"] = {
            "invalid_asset_ids": invalid_asset_ids_list,
            "outlier_temp_samples": temp_outliers.head(5)[["timestamp", "asset_id", "temperature"]].to_dict(orient="records"),
            "outlier_power_samples": power_outliers.head(5)[["timestamp", "asset_id", "power_consumption"]].to_dict(orient="records"),
            "late_arriving_samples": late_arriving.head(5)[["timestamp", "asset_id"]].to_dict(orient="records")
        }
        
        # 4. Check Events
        events_duplicates = int(df_events.duplicated().sum())
        events_nulls = df_events.isnull().sum().to_dict()
        
        event_assets = df_events["asset_id"].astype(str).str.strip()
        invalid_event_assets = df_events[~event_assets.isin(valid_asset_ids)]
        num_invalid_event_assets = len(invalid_event_assets)
        
        invalid_event_time_indices = check_timestamps(df_events, "timestamp")
        
        self.report["summary"]["events"] = {
            "total_records": len(df_events),
            "duplicates": events_duplicates,
            "missing_values": events_nulls,
            "invalid_asset_ids_count": num_invalid_event_assets,
            "invalid_timestamps_count": len(invalid_event_time_indices)
        }
        
        return self.report
        
    def save_report(self, output_path="data/data_quality_report.json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=4)
        print(f"Data Quality Report saved to {output_path}")

if __name__ == "__main__":
    dq = DataQualityFramework("data/assets_metadata.csv", "data/telemetry_raw.csv", "data/events_raw.csv")
    report = dq.run_checks()
    dq.save_report()
