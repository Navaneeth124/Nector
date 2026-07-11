import sqlite3
import networkx as nx

DB_PATH = "nectar_iot.db"

class AssetHierarchyGraph:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.load_graph_from_db()
        
    def load_graph_from_db(self):
        """Loads assets and relationships from dim_asset into a NetworkX DiGraph."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fetch all assets
        cursor.execute("SELECT asset_id, asset_name, asset_type, manufacturer, site_id, building_id, parent_asset_id FROM dim_asset")
        rows = cursor.fetchall()
        conn.close()
        
        self.graph.clear()
        
        # Add nodes with metadata
        for row in rows:
            asset_id, name, asset_type, manufacturer, site_id, building_id, parent_id = row
            self.graph.add_node(
                asset_id,
                name=name,
                type=asset_type,
                manufacturer=manufacturer,
                site_id=site_id,
                building_id=building_id,
                parent_asset_id=parent_id
            )
            
        # Add edges for hierarchy (parent -> child)
        for row in rows:
            asset_id, _, _, _, _, _, parent_id = row
            if parent_id and parent_id in self.graph:
                self.graph.add_edge(parent_id, asset_id)
                
    def get_assets_under_site(self, site_id):
        """Retrieves all assets associated with a specific site."""
        assets = []
        for node, data in self.graph.nodes(data=True):
            if data.get("site_id") == site_id:
                assets.append((node, data.get("name"), data.get("type")))
        return assets
        
    def get_parent_and_children(self, asset_id):
        """Retrieves the direct parent and children of a given asset."""
        if asset_id not in self.graph:
            return None, []
            
        # Parent (predecessors)
        parents = list(self.graph.predecessors(asset_id))
        parent = parents[0] if parents else None
        
        # Children (successors)
        children = list(self.graph.successors(asset_id))
        
        return parent, children
        
    def get_downstream_impacted(self, asset_id):
        """Finds all downstream assets recursively affected if the given asset fails."""
        if asset_id not in self.graph:
            return []
            
        # nx.descendants returns all nodes reachable from asset_id (recursive children)
        descendants = list(nx.descendants(self.graph, asset_id))
        return descendants
        
    def get_orphan_assets(self):
        """Identify assets that do not have site_id or building_id specified."""
        orphans = []
        for node, data in self.graph.nodes(data=True):
            site = data.get("site_id")
            bldg = data.get("building_id")
            if not site or not bldg:
                orphans.append((node, data.get("name"), data.get("type")))
        return orphans
        
    def get_disconnected_assets(self):
        """Identify assets that have site/building info, but no hierarchical edges in the graph."""
        disconnected = []
        for node, data in self.graph.nodes(data=True):
            # Must not be an orphan (must have site/building)
            if data.get("site_id") and data.get("building_id"):
                # Indegree (parents) and outdegree (children) must be 0
                if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0:
                    disconnected.append((node, data.get("name"), data.get("type")))
        return disconnected

# Self-test block
if __name__ == "__main__":
    hierarchy = AssetHierarchyGraph()
    print("--- 1. Assets under SITE_A ---")
    print(hierarchy.get_assets_under_site("SITE_A"))
    
    print("\n--- 2. Parent & Children for AHU-01 (ASSET_002) ---")
    parent, children = hierarchy.get_parent_and_children("ASSET_002")
    print(f"Parent: {parent}, Children: {children}")
    
    print("\n--- 3. Downstream impacted assets of Chiller-01 (ASSET_001) ---")
    print(hierarchy.get_downstream_impacted("ASSET_001"))
    
    print("\n--- 4. Orphan Assets ---")
    print(hierarchy.get_orphan_assets())
    
    print("\n--- 5. Disconnected Assets ---")
    print(hierarchy.get_disconnected_assets())
