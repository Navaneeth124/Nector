import os
import sqlite3
import unittest
from asset_graph import AssetHierarchyGraph

class TestNectarDataPlatform(unittest.TestCase):
    def setUp(self):
        self.db_path = "nectar_iot.db"
        self.assertTrue(os.path.exists(self.db_path), "Database file 'nectar_iot.db' does not exist. Run the pipeline first.")
        self.hierarchy = AssetHierarchyGraph(self.db_path)

    def test_database_tables_exist(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verify core tables
        tables = ["dim_site", "dim_building", "dim_asset", "dim_time", "fact_telemetry", "fact_energy", "fact_event"]
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            self.assertIsNotNone(cursor.fetchone(), f"Table '{table}' should exist in the database.")
            
        conn.close()

    def test_data_ingestion_and_cleaning(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verify sites and assets are loaded
        cursor.execute("SELECT COUNT(*) FROM dim_site")
        site_count = cursor.fetchone()[0]
        self.assertEqual(site_count, 2, "There should be exactly 2 registered sites (SITE_A and SITE_B).")
        
        cursor.execute("SELECT COUNT(*) FROM dim_asset")
        asset_count = cursor.fetchone()[0]
        self.assertEqual(asset_count, 10, "There should be exactly 10 registered assets in dim_asset.")
        
        # Verify telemetry facts are loaded
        cursor.execute("SELECT COUNT(*) FROM fact_telemetry")
        telemetry_count = cursor.fetchone()[0]
        self.assertTrue(telemetry_count > 0, "fact_telemetry table should not be empty.")
        
        conn.close()

    def test_asset_graph_hierarchy(self):
        # 1. Test get assets under site
        site_a_assets = self.hierarchy.get_assets_under_site("SITE_A")
        asset_ids = [asset[0] for asset in site_a_assets]
        self.assertIn("ASSET_001", asset_ids, "Chiller-01 (ASSET_001) should be under SITE_A.")
        self.assertIn("ASSET_002", asset_ids, "AHU-01 (ASSET_002) should be under SITE_A.")
        
        # 2. Test parent and child relations
        parent, children = self.hierarchy.get_parent_and_children("ASSET_002") # AHU-01
        self.assertEqual(parent, "ASSET_001", "Parent of AHU-01 should be Chiller-01 (ASSET_001).")
        self.assertEqual(len(children), 0, "AHU-01 should have no children.")
        
        # 3. Test downstream impact analysis
        impacted = self.hierarchy.get_downstream_impacted("ASSET_001") # Chiller-01
        self.assertIn("ASSET_002", impacted, "AHU-01 should be impacted if Chiller-01 fails.")
        self.assertIn("ASSET_003", impacted, "AHU-02 should be impacted if Chiller-01 fails.")
        self.assertEqual(len(impacted), 2, "Exactly 2 assets should be downstream of Chiller-01.")
        
        # 4. Test orphan assets detection
        orphans = self.hierarchy.get_orphan_assets()
        orphan_ids = [asset[0] for asset in orphans]
        self.assertIn("ASSET_009", orphan_ids, "ASSET_009 (Exhaust Fan) should be detected as an orphan asset.")
        self.assertEqual(len(orphans), 1, "There should be exactly 1 orphan asset in mock data.")
        
        # 5. Test disconnected assets detection
        disconnected = self.hierarchy.get_disconnected_assets()
        disconnected_ids = [asset[0] for asset in disconnected]
        self.assertIn("ASSET_008", disconnected_ids, "ASSET_008 (Pump-02) should be detected as disconnected.")
        self.assertIn("ASSET_010", disconnected_ids, "ASSET_010 (Emergency Generator) should be detected as disconnected.")
        self.assertEqual(len(disconnected), 2, "There should be exactly 2 disconnected assets.")

if __name__ == "__main__":
    print("Running automated test runner...")
    unittest.main()
