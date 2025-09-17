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

# --- BUILD ADJACENCY GRAPH ---
graph = Graph.from_geodataframe(gdf)
for node, row in gdf.iterrows():
    graph.nodes[node]["population"] = row[POP_COL]

# --- RECURSIVE TREE PARTITIONING ---
total_pop = sum(graph.nodes[n]["population"] for n in graph.nodes)
ideal_pop = total_pop / NUM_DISTRICTS

# Use a very tight population deviation (1%)
assignment = recursive_tree_part(
    graph,
    parts=list(range(NUM_DISTRICTS)),
    pop_col="population",
    pop_target=ideal_pop,
    epsilon=0.01,  # 1% deviation
    node_repeats=1
)

# TODO: VRA/minority opportunity analysis and county split minimization

# --- OUTPUT ASSIGNMENT TO CSV ---
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

# --- Homogeneity index (within-district variance of racial/ethnic shares) ---
for group in ["pop_white", "pop_black", "pop_hisp"]:
    merged[f"{group}_share"] = merged[group] / merged["pop"]
homogeneity = merged.groupby("district").agg({
    "pop_white_share": "var",
    "pop_black_share": "var",
    "pop_hisp_share": "var"
}).mean(axis=1)
print("\nMean within-district demographic variance (homogeneity index): {:.4f}".format(homogeneity.mean()))

# --- Efficiency gap ---
total_votes = merged["pre_20_dem_bid"] + merged["pre_20_rep_tru"]
merged["dem_margin"] = merged["pre_20_dem_bid"] - merged["pre_20_rep_tru"]
district_votes["total_votes"] = district_votes["pre_20_dem_bid"] + district_votes["pre_20_rep_tru"]
district_votes["dem_wasted"] = district_votes.apply(lambda r: r["pre_20_dem_bid"] - r["total_votes"]//2 if r["dem_share"] > 0.5 else r["pre_20_dem_bid"], axis=1)
district_votes["rep_wasted"] = district_votes.apply(lambda r: r["pre_20_rep_tru"] - r["total_votes"]//2 if r["dem_share"] < 0.5 else r["pre_20_rep_tru"], axis=1)
egap = (district_votes["rep_wasted"].sum() - district_votes["dem_wasted"].sum()) / district_votes["total_votes"].sum()
print(f"\nEfficiency gap: {egap:.4f}")

# --- Mean–median difference ---
mean_share = district_votes["dem_share"].mean()
median_share = district_votes["dem_share"].median()
mm_diff = mean_share - median_share
print(f"Mean–median difference: {mm_diff:.4f}")

# --- Competitiveness (districts with 45% < Dem share < 55%) ---
competitive = ((district_votes["dem_share"] > 0.45) & (district_votes["dem_share"] < 0.55)).sum()
print(f"Competitive districts (45–55% Dem share): {competitive}")

# --- Compactness (Polsby-Popper) ---
gdf = gpd.read_file(SHAPEFILE)
gdf = gdf.merge(assignment_df, on="GEOID20")
district_shapes = gdf.dissolve(by="district")
district_shapes = district_shapes.to_crs(epsg=6933)  # Equal-area projection for area/perimeter
district_shapes["area"] = district_shapes.geometry.area
district_shapes["perim"] = district_shapes.geometry.length
district_shapes["polsby_popper"] = 4 * 3.141592653589793 * district_shapes["area"] / (district_shapes["perim"] ** 2)
print("\nMean Polsby-Popper compactness: {:.4f}".format(district_shapes["polsby_popper"].mean()))
