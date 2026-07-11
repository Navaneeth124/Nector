-- SQL Challenge Queries for Nectar Data Engineer Challenge

-- 1. Find the top 10 assets with the highest energy consumption.
-- We sum the power consumption (multiplied by 0.25 for 15-minute readings to get kWh)
SELECT 
    fe.asset_id,
    da.asset_name,
    da.asset_type,
    da.site_id,
    ROUND(SUM(fe.power_consumption) * 0.25, 2) as total_energy_kwh
FROM fact_energy fe
JOIN dim_asset da ON fe.asset_id = da.asset_id
GROUP BY fe.asset_id, da.asset_name, da.asset_type, da.site_id
ORDER BY total_energy_kwh DESC
LIMIT 10;


-- 2. Calculate average daily energy consumption for each site.
-- First, get the daily sum of energy for each site, then average it.
WITH daily_site_energy AS (
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
GROUP BY site_id;


-- 3. Identify assets that generated more than 10 faults in the last 30 days.
-- Filters for event_type 'Fault' and checks timestamp ranges.
SELECT 
    fe.asset_id,
    da.asset_name,
    da.asset_type,
    COUNT(fe.event_id) as fault_count
FROM fact_event fe
JOIN dim_asset da ON fe.asset_id = da.asset_id
WHERE fe.event_type = 'Fault'
  AND datetime(fe.timestamp) >= datetime('now', '-30 days')
GROUP BY fe.asset_id, da.asset_name, da.asset_type
HAVING fault_count > 10;


-- 4. Find assets that have not reported telemetry for the last 24 hours.
-- Left joins assets with telemetry to find those with no reports in the last 24 hours or ever.
-- We use the maximum timestamp in the database as the reference point for "current time" 
-- to ensure queries work correctly even with historical mock data.
WITH max_db_time AS (
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
   OR datetime(last_reported_time) < datetime(mdt.max_time, '-24 hours');


-- 5. Calculate hourly utilization for each building.
-- Calculates the percentage of active readings (operating_mode = 'NORMAL') per building, per hour.
SELECT 
    building_id,
    strftime('%Y-%m-%d %H:00:00', timestamp) as hour_timestamp,
    COUNT(CASE WHEN operating_mode = 'NORMAL' THEN 1 END) as normal_readings,
    COUNT(*) as total_readings,
    ROUND(COUNT(CASE WHEN operating_mode = 'NORMAL' THEN 1 END) * 100.0 / COUNT(*), 2) as utilization_percentage
FROM fact_telemetry
WHERE building_id IS NOT NULL AND building_id != ''
GROUP BY building_id, hour_timestamp
ORDER BY building_id, hour_timestamp;


-- 6. Identify sites with abnormal increases in power consumption.
-- Compares daily energy consumption against the previous day using window functions (LAG).
-- Flags daily increases of more than 50% (1.5x).
WITH daily_site_energy AS (
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
  AND total_energy > prev_day_energy * 1.5; -- > 50% increase
