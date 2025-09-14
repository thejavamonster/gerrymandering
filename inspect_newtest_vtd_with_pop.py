import geopandas as gpd
import pandas as pd
import folium

# Load the new VTD shapefile
gdf = gpd.read_file('newtest/tl_2020_12_vtd20.shp')

# Load the VTD CSV with population and demographic data
vtd = pd.read_csv('fl_2020_vtd.csv', dtype={'GEOID20': str})

# Merge on GEOID20
merged = gdf.merge(vtd, on='GEOID20', how='left')

# Check join success
print(f"Precincts in shapefile: {len(gdf)}")
print(f"Precincts with population data after join: {merged['pop'].notnull().sum()}")

# Create interactive map with population tooltip
center = [merged.geometry.centroid.y.mean(), merged.geometry.centroid.x.mean()]
m = folium.Map(location=center, zoom_start=7)


folium.GeoJson(
    merged,
    name='VTDs',
    tooltip=folium.GeoJsonTooltip(
        fields=['GEOID20', 'pop', 'county', 'pre_20_rep_tru', 'pre_20_dem_bid'],
        aliases=['VTD GEOID:', 'Population:', 'County:', 'Trump 2020:', 'Biden 2020:'],
        localize=True
    )
).add_to(m)

m.save('vtds_interactive_map.html')
print('Interactive map saved as vtds_interactive_map.html. Open this file in your browser to explore population by VTD.')
