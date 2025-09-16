import geopandas as gpd
import pandas as pd
import folium

# Load merged VTDs and extreme district assignment
merged = gpd.read_file("merged_vtds.shp")
districts = pd.read_csv("district_assignment_contig_extreme.csv")

# Merge assignment into GeoDataFrame
merged = merged.merge(districts, on="GEOID20")

# Dissolve to district geometries and sum population
district_map = merged.dissolve(by="district", aggfunc={"pop": "sum"})
district_map = district_map.reset_index()

# Create folium map centered on Florida
center = [merged.geometry.centroid.y.mean(), merged.geometry.centroid.x.mean()]
m = folium.Map(location=center, zoom_start=7, tiles="cartodbpositron")

# Add districts to map
folium.Choropleth(
    geo_data=district_map,
    name="Districts",
    data=district_map,
    columns=["district", "pop"],
    key_on="feature.properties.district",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="District Population"
).add_to(m)

# Add hover tooltips
for _, row in district_map.iterrows():
    folium.GeoJson(
        row["geometry"],
        name=f"District {row['district']}",
        tooltip=folium.Tooltip(f"District: {row['district']}<br>Population: {int(row['pop'])}")
    ).add_to(m)

m.save("extreme_gerrymandered_districts.html")
print("Interactive map saved as extreme_gerrymandered_districts.html")
