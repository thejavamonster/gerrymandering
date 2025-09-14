import geopandas as gpd
import pandas as pd
import folium
import numpy as np

# Load the joined VTD shapefile and CSV
gdf = gpd.read_file('newtest/tl_2020_12_vtd20.shp')
vtd = pd.read_csv('fl_2020_vtd.csv', dtype={'GEOID20': str})
merged = gdf.merge(vtd, on='GEOID20', how='left')

# Calculate county-level total votes for Trump and Biden
county_votes = merged.groupby('county')[['pre_20_rep_tru', 'pre_20_dem_bid']].sum().reset_index()
county_votes['margin'] = county_votes['pre_20_rep_tru'] - county_votes['pre_20_dem_bid']
county_votes['total'] = county_votes['pre_20_rep_tru'] + county_votes['pre_20_dem_bid']
county_votes['lean'] = county_votes['margin'] / county_votes['total']

# Assign color: blue for Biden, red for Trump, purple for close
# We'll use a linear interpolation between blue and red
from matplotlib.colors import to_hex
import matplotlib.pyplot as plt

def lean_to_color(lean):
    # lean: -1 (blue) to +1 (red)
    # Map -1 to blue, 0 to purple, +1 to red
    cmap = plt.get_cmap('bwr')
    # Normalize lean to [0,1] for colormap
    norm_lean = (lean + 1) / 2
    return to_hex(cmap(norm_lean))

county_votes['color'] = county_votes['lean'].apply(lean_to_color)

# Map color to each precinct by county
county_color_map = dict(zip(county_votes['county'], county_votes['color']))
merged['county_color'] = merged['county'].map(county_color_map)

# Center map
center = [merged.geometry.centroid.y.mean(), merged.geometry.centroid.x.mean()]
m = folium.Map(location=center, zoom_start=7)

folium.GeoJson(
    merged,
    name='Counties',
    style_function=lambda feature: {
        'fillColor': feature['properties']['county_color'] or '#cccccc',
        'color': 'black',
        'weight': 0.2,
        'fillOpacity': 0.3
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['GEOID20', 'pop', 'county', 'pre_20_rep_tru', 'pre_20_dem_bid'],
        aliases=['VTD GEOID:', 'Population:', 'County:', 'Trump 2020:', 'Biden 2020:'],
        localize=True
    )
).add_to(m)

m.save('county_partisan_lean_map.html')
print('Map saved as county_partisan_lean_map.html. Open this file in your browser to view county partisan lean.')
