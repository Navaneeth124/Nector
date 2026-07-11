import os
import csv
import random
from datetime import datetime, timedelta

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# 1. Generate Asset Metadata
# Site A: Building-1 -> Chiller-01 -> AHU-01, AHU-02
# Site A: Building-1 -> Pump-01 -> Flow Sensor-01
# Site B: Building-2 -> Chiller-02 -> AHU-03
# Site B: Building-2 -> Pump-02
# Orphan Assets: Asset with no site/building info
# Disconnected Assets: Asset with no parent/child relationships (isolated)
assets = [
    # Site A - Building 1
    {"asset_id": "ASSET_001", "asset_name": "Chiller-01", "asset_type": "Chiller", "manufacturer": "Carrier", "installation_date": "2024-01-15", "site_id": "SITE_A", "building_id": "BLDG_1", "parent_asset_id": None},
    {"asset_id": "ASSET_002", "asset_name": "AHU-01", "asset_type": "AHU", "manufacturer": "Trane", "installation_date": "2024-02-10", "site_id": "SITE_A", "building_id": "BLDG_1", "parent_asset_id": "ASSET_001"},
    {"asset_id": "ASSET_003", "asset_name": "AHU-02", "asset_type": "AHU", "manufacturer": "Trane", "installation_date": "2024-02-11", "site_id": "SITE_A", "building_id": "BLDG_1", "parent_asset_id": "ASSET_001"},
    {"asset_id": "ASSET_004", "asset_name": "Pump-01", "asset_type": "Pump", "manufacturer": "Grundfos", "installation_date": "2023-11-05", "site_id": "SITE_A", "building_id": "BLDG_1", "parent_asset_id": None},
    {"asset_id": "ASSET_005", "asset_name": "Flow Sensor-01", "asset_type": "Sensor", "manufacturer": "Siemens", "installation_date": "2024-03-01", "site_id": "SITE_A", "building_id": "BLDG_1", "parent_asset_id": "ASSET_004"},
    
    # Site B - Building 2
    {"asset_id": "ASSET_006", "asset_name": "Chiller-02", "asset_type": "Chiller", "manufacturer": "York", "installation_date": "2022-08-20", "site_id": "SITE_B", "building_id": "BLDG_2", "parent_asset_id": None},
    {"asset_id": "ASSET_007", "asset_name": "AHU-03", "asset_type": "AHU", "manufacturer": "Carrier", "installation_date": "2023-05-12", "site_id": "SITE_B", "building_id": "BLDG_2", "parent_asset_id": "ASSET_006"},
    {"asset_id": "ASSET_008", "asset_name": "Pump-02", "asset_type": "Pump", "manufacturer": "Grundfos", "installation_date": "2022-09-01", "site_id": "SITE_B", "building_id": "BLDG_2", "parent_asset_id": None},
    
    # Orphan Assets (No Site or Building ID)
    {"asset_id": "ASSET_009", "asset_name": "Exhaust Fan-01", "asset_type": "Fan", "manufacturer": "Greenheck", "installation_date": "2023-07-22", "site_id": "", "building_id": "", "parent_asset_id": None},
    
    # Disconnected Assets (Has Site/Building but no links, or isolated)
    {"asset_id": "ASSET_010", "asset_name": "Emergency Generator", "asset_type": "Generator", "manufacturer": "Caterpillar", "installation_date": "2021-12-10", "site_id": "SITE_A", "building_id": "BLDG_1", "parent_asset_id": None},
]

with open("data/assets_metadata.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["asset_id", "asset_name", "asset_type", "manufacturer", "installation_date", "site_id", "building_id", "parent_asset_id"])
    writer.writeheader()
    writer.writerows(assets)

# 2. Generate IoT Telemetry
# Generate data for the last 3 days at 15-minute intervals
start_time = datetime.now() - timedelta(days=3)
end_time = datetime.now()

telemetry_data = []
current_time = start_time

# Track sensor IDs
sensors = {
    "ASSET_001": "SENS_CH1",
    "ASSET_002": "SENS_AH1",
    "ASSET_003": "SENS_AH2",
    "ASSET_004": "SENS_P1",
    "ASSET_005": "SENS_FS1",
    "ASSET_006": "SENS_CH2",
    "ASSET_007": "SENS_AH3",
    "ASSET_008": "SENS_P2",
    "ASSET_010": "SENS_GEN",
}

# Add some invalid assets in telemetry to test validation
invalid_assets = ["ASSET_999", "ASSET_XYZ"]

print("Generating telemetry data...")

# Generate time series
while current_time < end_time:
    for asset in assets:
        if not asset["site_id"] or asset["asset_id"] == "ASSET_009": # Skip orphan for telemetry or generate empty/faulty
            continue
            
        asset_id = asset["asset_id"]
        sensor_id = sensors.get(asset_id, "SENS_GEN")
        
        # Base values depending on asset type
        if asset["asset_type"] == "Chiller":
            base_temp = 7.0 + random.uniform(-1.0, 1.0) # Chilled water temp
            base_humidity = 45.0 + random.uniform(-5.0, 5.0)
            base_press = 350.0 + random.uniform(-20.0, 20.0)
            base_vib = 1.2 + random.uniform(-0.2, 0.2)
            base_power = 150.0 + random.uniform(-10.0, 10.0) # kW
        elif asset["asset_type"] == "AHU":
            base_temp = 22.0 + random.uniform(-1.0, 1.0)
            base_humidity = 50.0 + random.uniform(-5.0, 5.0)
            base_press = 101.3 + random.uniform(-1.0, 1.0)
            base_vib = 0.5 + random.uniform(-0.1, 0.1)
            base_power = 15.0 + random.uniform(-2.0, 2.0)
        elif asset["asset_type"] == "Pump":
            base_temp = 35.0 + random.uniform(-3.0, 3.0)
            base_humidity = 55.0 + random.uniform(-5.0, 5.0)
            base_press = 400.0 + random.uniform(-30.0, 30.0)
            base_vib = 2.5 + random.uniform(-0.5, 0.5)
            base_power = 45.0 + random.uniform(-5.0, 5.0)
        else: # Sensor, Generator, etc.
            base_temp = 24.0 + random.uniform(-2.0, 2.0)
            base_humidity = 40.0 + random.uniform(-5.0, 5.0)
            base_press = 101.3 + random.uniform(-1.0, 1.0)
            base_vib = 0.1 + random.uniform(-0.05, 0.05)
            base_power = 2.0 + random.uniform(-0.5, 0.5)
            
        # Introduce power consumption spike/anomaly for Site B on Day 2
        # (For SQL challenge question 6: Identify sites with abnormal increases in power consumption)
        if asset["site_id"] == "SITE_B" and (start_time + timedelta(days=1) <= current_time <= start_time + timedelta(days=2)):
            base_power *= 2.5 # 250% increase
            
        # Create normal record
        record = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "site_id": asset["site_id"],
            "building_id": asset["building_id"],
            "asset_id": asset_id,
            "sensor_id": sensor_id,
            "temperature": round(base_temp, 2),
            "humidity": round(base_humidity, 2),
            "pressure": round(base_press, 2),
            "vibration": round(base_vib, 2),
            "power_consumption": round(base_power, 2),
            "operating_mode": "NORMAL" if random.random() > 0.1 else "STANDBY"
        }
        
        # Inject anomalies to test Task 2 & 5 (Data Quality)
        rand = random.random()
        if rand < 0.005:
            # Null/Missing value
            record["temperature"] = ""
        elif rand < 0.01:
            # Outlier temperature
            record["temperature"] = round(base_temp * 5.0, 2)
        elif rand < 0.015:
            # Invalid timestamp format
            record["timestamp"] = "INVALID_TIME"
        elif rand < 0.02:
            # Outlier power consumption
            record["power_consumption"] = round(base_power * 10.0, 2)
            
        telemetry_data.append(record)
        
        # Inject duplicates
        if rand < 0.005:
            telemetry_data.append(record.copy())
            
    # Inject telemetry for invalid asset IDs occasionally
    if random.random() < 0.02:
        telemetry_data.append({
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "site_id": "SITE_A",
            "building_id": "BLDG_1",
            "asset_id": random.choice(invalid_assets),
            "sensor_id": "SENS_ERR",
            "temperature": 25.0,
            "humidity": 50.0,
            "pressure": 100.0,
            "vibration": 0.5,
            "power_consumption": 10.0,
            "operating_mode": "NORMAL"
        })
        
    current_time += timedelta(minutes=15)

# Add some late arriving data (e.g. timestamp from 5 days ago, but placed at the end of stream)
late_timestamp = start_time - timedelta(days=2)
for i in range(5):
    telemetry_data.append({
        "timestamp": late_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "site_id": "SITE_A",
        "building_id": "BLDG_1",
        "asset_id": "ASSET_002",
        "sensor_id": "SENS_AH1",
        "temperature": 21.0,
        "humidity": 49.0,
        "pressure": 101.0,
        "vibration": 0.4,
        "power_consumption": 14.5,
        "operating_mode": "NORMAL"
    })

# Write Telemetry Data
with open("data/telemetry_raw.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "site_id", "building_id", "asset_id", "sensor_id", "temperature", "humidity", "pressure", "vibration", "power_consumption", "operating_mode"])
    writer.writeheader()
    writer.writerows(telemetry_data)


# 3. Generate Event Dataset
# Generate events/faults over the 3 day period.
# Specifically, we want some assets to have > 10 faults in the last 30 days (Task 6 Query 3).
# Since our data is 3 days, we'll generate high concentration of faults on "ASSET_002" (AHU-01) to exceed 10 faults.
events_data = []
event_types = ["Alarm", "Warning", "Fault"]
severities = ["Low", "Medium", "High"]
messages = {
    "Alarm": ["High temperature alarm", "Low pressure warning", "Filter replacement needed"],
    "Warning": ["Vibration slightly above threshold", "High humidity detected", "Standby mode timeout"],
    "Fault": ["Compressor failure", "Fan belt broken", "Communication lost", "Power supply fault"]
}

# Force inject 15 faults for ASSET_002 to ensure it has > 10 faults in the last 30 days
for i in range(15):
    fault_time = start_time + timedelta(hours=i*4 + 2)
    events_data.append({
        "event_id": f"EVT_F_{i:04d}",
        "timestamp": fault_time.strftime("%Y-%m-%d %H:%M:%S"),
        "asset_id": "ASSET_002",
        "event_type": "Fault",
        "severity": "High",
        "message": f"Forced compressor failure {i}"
    })

current_time = start_time
event_id_counter = 100

while current_time < end_time:
    # Randomly generate events for different assets
    for asset in assets:
        if not asset["site_id"] or asset["asset_id"] == "ASSET_009":
            continue
        
        asset_id = asset["asset_id"]
        
        # High fault asset: ASSET_002 will fail frequently
        fail_prob = 0.25 if asset_id == "ASSET_002" else 0.005
        
        if random.random() < fail_prob:
            e_type = random.choice(event_types)
            if asset_id == "ASSET_002":
                # Ensure we get many "Fault" types for Query 3
                e_type = "Fault"
            
            sev = random.choice(severities) if e_type != "Fault" else "High"
            msg = random.choice(messages[e_type])
            
            record = {
                "event_id": f"EVT_{event_id_counter:04d}",
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "asset_id": asset_id,
                "event_type": e_type,
                "severity": sev,
                "message": msg
            }
            events_data.append(record)
            event_id_counter += 1
            
            # Inject duplicate event to test validation
            if random.random() < 0.05:
                events_data.append(record.copy())
                
    current_time += timedelta(hours=1)

# Write Events Data
with open("data/events_raw.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["event_id", "timestamp", "asset_id", "event_type", "severity", "message"])
    writer.writeheader()
    writer.writerows(events_data)

print(f"Data generation complete! Generated {len(telemetry_data)} telemetry records and {len(events_data)} events.")
