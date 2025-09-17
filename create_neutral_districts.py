import geopandas as gpd
import pandas as pd
import networkx as nx
from gerrychain import Graph
from gerrychain.tree import recursive_tree_part
import pickle

# --- PARAMETERS ---
SHAPEFILE = "merged_vtds.shp"
OUTPUT_CSV = "neutral_district_assignment.csv"
NUM_DISTRICTS = 28  # Set as needed
POP_COL = "pop"


# --- LOAD SHAPEFILE ---
gdf = gpd.read_file(SHAPEFILE)
gdf = gdf.set_index("GEOID20")

# Fix invalid geometries
invalid_count = (~gdf.is_valid).sum()
if invalid_count > 0:
    print(f"Fixing {invalid_count} invalid geometries...")
    gdf["geometry"] = gdf["geometry"].buffer(0)

# Buffer geometries slightly to ensure robust adjacency
gdf["geometry"] = gdf["geometry"].buffer(0.0001)

# --- LOAD SHAPEFILE ---

# --- BUILD ROBUST ADJACENCY GRAPH ---
import networkx as nx
# --- BUILD ADJACENCY GRAPH (original method) ---
from gerrychain import Graph
graph = Graph.from_geodataframe(gdf)

for node, row in gdf.iterrows():
    graph.nodes[node]["population"] = row[POP_COL]

# Calculate ideal population per district
ideal_pop = gdf[POP_COL].sum() / NUM_DISTRICTS

# Assign districts using recursive_tree_part
assignment = recursive_tree_part(
    graph,
    parts=list(range(NUM_DISTRICTS)),
    pop_col="population",
    pop_target=ideal_pop,
    epsilon=0.02,  # 2% deviation, adjust as needed
    node_repeats=1
)

# Create assignment DataFrame
assignment_df = pd.DataFrame({
    "GEOID20": list(assignment.keys()),
    "district": list(assignment.values())
})

assignment_df.to_csv(OUTPUT_CSV, index=False)
print(f"Neutral district assignment saved to {OUTPUT_CSV}")

# --- POST-ASSIGNMENT ANALYSIS ---
vtd_data = pd.read_csv("fl_2020_vtd.csv")
merged = assignment_df.merge(vtd_data, on="GEOID20")

# Population deviation by district
district_pops = merged.groupby("district")["pop"].sum()
ideal_pop = district_pops.sum() / NUM_DISTRICTS
deviations = (district_pops - ideal_pop).abs() / ideal_pop
print("\nPopulation deviation by district:")
print(deviations.describe())

# County splits: how many districts each county is split into
county_splits = merged.groupby("county")["district"].nunique()
print("\nCounty splits (number of districts per county):")
print(county_splits.value_counts().sort_index())

# Minority opportunity: districts where Black or Hispanic VAP >= 50%
merged["vap_black_share"] = merged["vap_black"] / merged["vap"]
merged["vap_hisp_share"] = merged["vap_hisp"] / merged["vap"]
district_vap = merged.groupby("district").agg({
    "vap": "sum",
    "vap_black": "sum",
    "vap_hisp": "sum"
})
district_vap["black_share"] = district_vap["vap_black"] / district_vap["vap"]
district_vap["hisp_share"] = district_vap["vap_hisp"] / district_vap["vap"]
opportunity = (district_vap[["black_share", "hisp_share"]] >= 0.5).any(axis=1)
print(f"\nMinority opportunity districts (VAP >= 50%): {opportunity.sum()} / {NUM_DISTRICTS}")

# Partisan seat share: use 2020 Pres (pre_20_dem_bid, pre_20_rep_tru)
district_votes = merged.groupby("district").agg({
    "pre_20_dem_bid": "sum",
    "pre_20_rep_tru": "sum"
})
district_votes["dem_share"] = district_votes["pre_20_dem_bid"] / (district_votes["pre_20_dem_bid"] + district_votes["pre_20_rep_tru"])
district_votes["winner"] = district_votes["dem_share"].apply(lambda x: "Dem" if x > 0.5 else "Rep")
seat_counts = district_votes["winner"].value_counts()

print(f"\nDistrict seat counts (2020 Pres):\n{seat_counts}")

# Statewide Dem share vs seat share
statewide_dem = merged["pre_20_dem_bid"].sum() / (merged["pre_20_dem_bid"].sum() + merged["pre_20_rep_tru"].sum())
dem_seat_share = (district_votes["winner"] == "Dem").mean()
print(f"\nStatewide Dem share: {statewide_dem:.3f}")
print(f"Democratic seat share: {dem_seat_share:.3f}")

# --- Community: Homogeneity index (variance of racial/ethnic shares within each district) ---
def homogeneity_index(df, group_col, pop_col, district_col="district"):
    df = df.copy()
    df["share"] = df[group_col] / df[pop_col]
    return df.groupby(district_col)["share"].var().mean()

homog_black = homogeneity_index(merged, "pop_black", "pop", "district")
homog_hisp = homogeneity_index(merged, "pop_hisp", "pop", "district")
homog_white = homogeneity_index(merged, "pop_white", "pop", "district")
print(f"\nHomogeneity index (mean within-district variance):")
print(f"  Black share: {homog_black:.4f}")
print(f"  Hispanic share: {homog_hisp:.4f}")
print(f"  White share: {homog_white:.4f}")

# --- Competitiveness: count of competitive districts (Dem share 45-55%) ---
competitive = ((district_votes["dem_share"] >= 0.45) & (district_votes["dem_share"] <= 0.55)).sum()
print(f"\nCompetitive districts (Dem share 45-55%): {competitive} / {NUM_DISTRICTS}")

# --- Compactness (Polsby-Popper) ---

# --- Compactness (Polsby-Popper) ---
import numpy as np
import geopandas as gpd
district_shapes = merged.merge(gdf.reset_index()[["GEOID20", "geometry"]], on="GEOID20")
# Project to a Florida-appropriate CRS for area/perimeter (EPSG:3086 = NAD83 / Florida GDL Albers)
district_shapes = district_shapes.set_geometry("geometry").to_crs(epsg=3086)
district_gdf = district_shapes.dissolve(by="district")
district_gdf["area"] = district_gdf.geometry.area
district_gdf["perimeter"] = district_gdf.geometry.length
district_gdf["polsby_popper"] = 4 * np.pi * district_gdf["area"] / (district_gdf["perimeter"] ** 2)

print("\nLeast compact districts (Polsby-Popper):")
print(district_gdf["polsby_popper"].sort_values().head(5))

# --- Check for non-contiguous (MultiPolygon) districts ---
from shapely.geometry import MultiPolygon
noncontig = district_gdf[district_gdf.geometry.type == "MultiPolygon"]
if not noncontig.empty:
    print("\nWARNING: The following districts are not contiguous (contain holes or enclaves):")
    print(noncontig.index.tolist())
else:

        print("\nChecking for VTDs with zero or only one neighbor in the adjacency graph...")
        zero_neighbors = [n for n in graph.nodes if len(list(graph.neighbors(n))) == 0]
        one_neighbor = [n for n in graph.nodes if len(list(graph.neighbors(n))) == 1]
        if zero_neighbors:
            print(f"VTDs with ZERO neighbors (possible islands or geometry errors): {zero_neighbors}")
        else:
            print("No VTDs with zero neighbors.")
        if one_neighbor:
            print(f"VTDs with only ONE neighbor (possible bridges or slivers): {one_neighbor[:20]} ... (total: {len(one_neighbor)})")
        else:
            print("No VTDs with only one neighbor.")
