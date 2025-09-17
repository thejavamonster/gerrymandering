import geopandas as gpd
import matplotlib.pyplot as plt

# --- PARAMETERS ---
SHAPEFILE = "merged_vtds.shp"

# --- LOAD SHAPEFILE ---
gdf = gpd.read_file(SHAPEFILE)

# Check for non-contiguous (MultiPolygon) VTDs
noncontig = gdf[gdf.geometry.type == "MultiPolygon"]
print(f"Total VTDs: {len(gdf)}")
print(f"Non-contiguous (MultiPolygon) VTDs: {len(noncontig)}")
if not noncontig.empty:
    print("List of non-contiguous VTD GEOID20s:")
    print(noncontig['GEOID20'].tolist())

# Plot all VTDs
fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(ax=ax, color='lightgray', edgecolor='black', linewidth=0.2)
if not noncontig.empty:
    noncontig.plot(ax=ax, color='red')
plt.title("Florida VTDs (red = non-contiguous)")
plt.axis('off')
plt.tight_layout()
plt.show()
