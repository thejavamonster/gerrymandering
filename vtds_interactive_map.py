import geopandas as gpd
import pandas as pd
import folium
from folium.features import GeoJsonTooltip

# --- PARAMETERS ---
SHAPEFILE = "merged_vtds.shp"
OUTPUT_HTML = "vtds_interactive_map.html"

# --- LOAD SHAPEFILE ---
gdf = gpd.read_file(SHAPEFILE)

# Prepare tooltip fields (show GEOID20, county, pop, pop_white, pop_black, pop_hisp, pre_20_dem_bid, pre_20_rep_tru)
tooltip_fields = [
    "GEOID20",
    "county",
    "pop",
    "pop_white",
    "pop_black",
    "pop_hisp",
    "pre_20_dem",
    "pre_20_rep"
]
tooltip_aliases = [
    "GEOID20",
    "County",
    "Population",
    "White Pop",
    "Black Pop",
    "Hispanic Pop",
    "2020 Dem Votes",
    "2020 Rep Votes"
]

# Calculate map center
center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]

# Create Folium map
m = folium.Map(location=center, zoom_start=7, tiles="cartodbpositron")

folium.GeoJson(
    gdf,
    tooltip=GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True, sticky=True, labels=True, style=("background-color: white;")),
    style_function=lambda feature: {
        'fillColor': '#cccccc',
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.5
    }
).add_to(m)

m.save(OUTPUT_HTML)
print(f"Interactive VTD map saved to {OUTPUT_HTML}")
