import geopandas as gpd
import networkx as nx
from gerrychain import Graph

# Load merged shapefile (created in preprocess_vtd_data.py)
merged = gpd.read_file("merged_vtds.shp")

# Set index to GEOID20 so graph nodes use GEOID20 as keys
merged = merged.set_index("GEOID20")


# Build adjacency graph (nodes will be GEOID20)
graph = Graph.from_geodataframe(merged)

# Attach population and partisan vote attributes to each node
for node, row in merged.iterrows():
	graph.nodes[node]["population"] = row["pop"]  # Adjust column name as needed
	graph.nodes[node]["dem"] = row["pre_20_dem"]
	graph.nodes[node]["rep"] = row["pre_20_rep"]

# Save graph for use in gerrymandering pipeline
import pickle
with open("vtd_graph.gpickle", "wb") as f:
	pickle.dump(graph, f)
print("Adjacency graph created and saved as vtd_graph.gpickle.")
