import geopandas as gpd
import pandas as pd
import folium
from folium.features import GeoJsonTooltip

# --- PARAMETERS ---
SHAPEFILE = "merged_vtds.shp"
ASSIGNMENT_CSV = "neutral_district_assignment.csv"
VTD_DATA_CSV = "fl_2020_vtd.csv"
OUTPUT_HTML = "neutral_districts_interactive_map.html"

# --- LOAD DATA ---
gdf = gpd.read_file(SHAPEFILE)
assignments = pd.read_csv(ASSIGNMENT_CSV)
vtd_data = pd.read_csv(VTD_DATA_CSV)

# Merge assignments and VTD data into geodataframe
gdf = gdf.merge(assignments, left_on="GEOID20", right_on="GEOID20")
gdf = gdf.merge(vtd_data, left_on="GEOID20", right_on="GEOID20")
# DEBUG: Print columns to check available fields
print("Columns after merging:", gdf.columns.tolist())

# Aggregate district-level stats

district_stats = gdf.groupby("district").agg({
    "pop_y": "sum",
    "pop_white_y": "sum",
    "pop_black_y": "sum",
    "pop_hisp_y": "sum",
    "pre_20_dem_bid": "sum",
    "pre_20_rep_tru": "sum"
}).reset_index()
district_stats["pct_white"] = 100*district_stats["pop_white_y"] / district_stats["pop_y"]
district_stats["pct_black"] = 100*district_stats["pop_black_y"] / district_stats["pop_y"]
district_stats["pct_hisp"] = 100*district_stats["pop_hisp_y"] / district_stats["pop_y"]
district_stats["dem_share"] = 100*district_stats["pre_20_dem_bid"] / (district_stats["pre_20_dem_bid"] + district_stats["pre_20_rep_tru"])
district_stats["rep_share"] = 100*district_stats["pre_20_rep_tru"] / (district_stats["pre_20_dem_bid"] + district_stats["pre_20_rep_tru"])


# Merge district stats back to geodataframe
gdf = gdf.merge(district_stats, on="district", suffixes=("", "_district"))


# Dissolve to district geometries and keep aggregated stats
district_gdf = gdf.dissolve(by="district", as_index=False, aggfunc={
    'pop_y': 'first',  # Will overwrite below
    'pct_white': 'first',
    'pct_black': 'first',
    'pct_hisp': 'first',
    'dem_share': 'first',
    'rep_share': 'first'
})
# Overwrite with correct aggregated values from district_stats
district_gdf = district_gdf.merge(district_stats, on="district", suffixes=("", "_agg"))

# Prepare tooltip fields (use aggregated values)
tooltip_fields = [
    "district",
    "pop_y_agg",
    "pct_white",
    "pct_black",
    "pct_hisp",
    "dem_share",
    "rep_share"
]
tooltip_aliases = [
    "District",
    "Population",
    "% White",
    "% Black",
    "% Hispanic",
    "Dem Share",
    "Rep Share"
]


# --- Color districts by partisan lean (blue to red) ---
import branca.colormap as cm
import numpy as np

# Calculate map center from district centroids
center = [district_gdf.geometry.centroid.y.mean(), district_gdf.geometry.centroid.x.mean()]

# Use dem_share_agg for coloring (0 = all R, 100 = all D)
colormap = cm.LinearColormap(["red", "white", "blue"], vmin=0, vmax=100)

def get_color(feature):
    share = feature["properties"]["dem_share_agg"]
    return colormap(share)

m = folium.Map(location=center, zoom_start=7, tiles="cartodbpositron")

folium.GeoJson(
    district_gdf,
    tooltip=GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True, sticky=True, labels=True, style=("background-color: white;")),
    style_function=lambda feature: {
        'fillColor': get_color(feature),
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.7
    }
).add_to(m)

colormap.caption = 'Democratic Vote Share (%)'
colormap.add_to(m)

m.save(OUTPUT_HTML)
print(f"Interactive map saved to {OUTPUT_HTML}")

# --- Print summary of districts and seat counts ---
district_gdf["lean"] = np.where(district_gdf["dem_share_agg"] > 50, "Democratic", "Republican")
district_gdf["margin"] = np.abs(district_gdf["dem_share_agg"] - 50)
summary = district_gdf[["district", "dem_share_agg", "rep_share_agg", "lean", "margin"]].sort_values("dem_share_agg", ascending=False)
print("\nDistrict Partisan Leans:")
print(summary.to_string(index=False, float_format="%.2f"))
num_dem = (district_gdf["lean"] == "Democratic").sum()
num_rep = (district_gdf["lean"] == "Republican").sum()
print(f"\nDemocratic seats: {num_dem}")
print(f"Republican seats: {num_rep}")
