import geopandas as gpd
import pandas as pd

# Load VTD shapefile (Florida 2020 VTDs)
vtds = gpd.read_file("newtest/tl_2020_12_vtd20.shp")

# Load election data (precinct-level or VTD-level)
election = pd.read_csv("fl_2020_vtd.csv")

# Merge on a common key (assume 'GEOID20' in shapefile, 'GEOID20' in CSV)
merged = vtds.merge(election, on="GEOID20")

# Print a summary to check
print(merged.head())
print(merged.columns)

# Save merged GeoDataFrame for next steps
merged.to_file("merged_vtds.shp")
