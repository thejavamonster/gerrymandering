import pickle
import pandas as pd
import geopandas as gpd
import networkx as nx
from collections import defaultdict

# Load graph and merged data
graph = pickle.load(open("vtd_graph.gpickle", "rb"))
merged = gpd.read_file("merged_vtds.shp")

NUM_DISTRICTS = 27
POP_COL = "pop"
REP_COL = "pre_20_rep"
DEM_COL = "pre_20_dem"

districts = defaultdict(list)
district_pops = defaultdict(int)
assignment = {}

# --- Pack-then-crack algorithm ---
# 1. Pack the most Democratic VTDs into as few districts as possible
NUM_DEM_PACKED = 2  # Change this to 1 for max GOP, or higher for more Dem seats
merged["lean"] = merged[DEM_COL] - merged[REP_COL]  # Dem-leaning most negative
sorted_vtds = merged.sort_values("lean", ascending=True)  # Most Dem first

# Calculate ideal population per district
ideal_pop = merged[POP_COL].sum() / NUM_DISTRICTS

# Pack Dems
packed = set()
assignment = {}
for d in range(NUM_DEM_PACKED):
    pop = 0
    for idx, row in sorted_vtds.iterrows():
        geoid = row["GEOID20"]
        if geoid in packed:
            continue
        if pop + row[POP_COL] > ideal_pop * 1.05:  # allow slight overfill
            break
        assignment[geoid] = d
        packed.add(geoid)
        pop += row[POP_COL]

# 2. Assign the rest to maximize Republican seats (crack Dems)
remaining = [row for idx, row in sorted_vtds.iterrows() if row["GEOID20"] not in packed]
num_gop_districts = NUM_DISTRICTS - NUM_DEM_PACKED
gop_districts = [d for d in range(NUM_DEM_PACKED, NUM_DISTRICTS)]
district_pops = {d: 0 for d in gop_districts}
districts = {d: [] for d in gop_districts}
for row in remaining:
    geoid = row["GEOID20"]
    # Assign to GOP district with lowest population
    min_district = min(district_pops, key=district_pops.get)
    assignment[geoid] = min_district
    districts[min_district].append(geoid)
    district_pops[min_district] += row[POP_COL]

# Save assignment

assign_df = pd.DataFrame(list(assignment.items()), columns=["GEOID20", "district"])
assign_df["GEOID20"] = assign_df["GEOID20"].astype(str)
merged["GEOID20"] = merged["GEOID20"].astype(str)
assign_df.to_csv("district_assignment_extreme.csv", index=False)
print("Extreme gerrymandered assignment saved to district_assignment_extreme.csv")

# Debug: print sample GEOID20s from both DataFrames
print("Sample GEOID20s in merged:", merged["GEOID20"].head().tolist())
print("Sample GEOID20s in assign_df:", assign_df["GEOID20"].head().tolist())

# Summarize seats
results = merged.join(assign_df.set_index("GEOID20"), on="GEOID20")
grouped = results.groupby("district").agg({REP_COL: "sum", DEM_COL: "sum"})
grouped["winner"] = grouped.apply(lambda row: "Republican" if row[REP_COL] > row[DEM_COL] else "Democrat", axis=1)
print("\nSeat counts by party:")
print(grouped["winner"].value_counts())
print("\nDistrict winners:")
print(grouped["winner"])
