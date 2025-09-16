import pickle
import pandas as pd
import geopandas as gpd
import networkx as nx
from collections import defaultdict, deque

# Load data
with open("vtd_graph.gpickle", "rb") as f:
    graph = pickle.load(f)
merged = gpd.read_file("merged_vtds.shp")

NUM_DISTRICTS = 27
POP_COL = "pop"
REP_COL = "pre_20_rep"
DEM_COL = "pre_20_dem"


# Calculate ideal population per district
ideal_pop = merged[POP_COL].sum() / NUM_DISTRICTS
max_pop = ideal_pop * 1.15  # allow 15% deviation
min_pop = ideal_pop * 0.85


# Precompute GEOID20 to row dict for fast lookup
row_dict = {row["GEOID20"]: row for _, row in merged.iterrows()}


# Seed selection: pack up to 3 Dem districts, all others most Republican
NUM_DEM_PACKED = 2
merged["lean"] = merged[REP_COL] - merged[DEM_COL]
seeds = list(merged.sort_values("lean", ascending=False)["GEOID20"][:NUM_DISTRICTS-NUM_DEM_PACKED])
seeds += list(merged.sort_values("lean", ascending=True)["GEOID20"][:NUM_DEM_PACKED])

# Assignment structures
assignment = {}
district_pops = defaultdict(int)
districts = defaultdict(set)
frontiers = defaultdict(deque)
assigned = set()

# Initialize districts with seeds
for d, geoid in enumerate(seeds):
    assignment[geoid] = d
    district_pops[d] += int(row_dict[geoid][POP_COL])
    districts[d].add(geoid)
    assigned.add(geoid)
    # Add neighbors to frontier
    for nbr in graph.neighbors(geoid):
        if nbr not in assigned:
            frontiers[d].append(nbr)

progress = 0
# Greedy contiguous growing
while len(assignment) < len(merged):
    made_progress = False
    for d in range(NUM_DISTRICTS):
        # Only grow if under max_pop
        if district_pops[d] >= max_pop:
            continue
        # If frontier is empty, pick next most Republican unassigned VTD as new seed
        while not frontiers[d]:
            unassigned = [g for g in row_dict if g not in assigned]
            if not unassigned:
                break
            # Pick most Republican unassigned
            best_seed = max(unassigned, key=lambda g: row_dict[g][REP_COL] - row_dict[g][DEM_COL])
            assignment[best_seed] = d
            district_pops[d] += int(row_dict[best_seed][POP_COL])
            districts[d].add(best_seed)
            assigned.add(best_seed)
            for nbr in graph.neighbors(best_seed):
                if nbr not in assigned:
                    frontiers[d].append(nbr)
        # Pick best available neighbor for this district
        best_nbr = None
        best_score = -float('inf')
        for _ in range(len(frontiers[d])):
            nbr = frontiers[d].popleft()
            if nbr in assigned:
                continue
            row = row_dict[nbr]
            pop = int(row[POP_COL])
            lean = int(row[REP_COL]) - int(row[DEM_COL])
            # Prefer most Republican
            if lean > best_score and district_pops[d] + pop <= max_pop:
                best_score = lean
                best_nbr = nbr
            frontiers[d].append(nbr)  # keep in frontier for next round
        if best_nbr:
            assignment[best_nbr] = d
            district_pops[d] += int(row_dict[best_nbr][POP_COL])
            districts[d].add(best_nbr)
            assigned.add(best_nbr)
            made_progress = True
            # Add new neighbors
            for nbr2 in graph.neighbors(best_nbr):
                if nbr2 not in assigned:
                    frontiers[d].append(nbr2)
            progress += 1
            if progress % 100 == 0:
                print(f"Assigned {progress} VTDs / {len(merged)}...")

# --- Local search: try to flip border VTDs to maximize GOP seats ---
import random
import math
print("\nStarting advanced local search (multi-pass swaps + simulated annealing) to maximize GOP seats...")

def get_seat_count(assignment):
    temp_assign_df = pd.DataFrame(list(assignment.items()), columns=["GEOID20", "district"])
    temp_results = merged.merge(temp_assign_df, on="GEOID20")
    temp_grouped = temp_results.groupby("district").agg({REP_COL: "sum", DEM_COL: "sum"})
    temp_grouped["winner"] = temp_grouped.apply(lambda row: "Republican" if row[REP_COL] > row[DEM_COL] else "Democrat", axis=1)
    return (temp_grouped["winner"] == "Republican").sum(), temp_grouped

def is_contiguous(district_set, remove_geoid=None, add_geoid=None):
    # Check if a district remains contiguous after removing/adding a VTD
    nodes = set(district_set)
    if remove_geoid:
        nodes.discard(remove_geoid)
    if add_geoid:
        nodes.add(add_geoid)
    if not nodes:
        return True
    start = next(iter(nodes))
    seen = set([start])
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nbr in graph.neighbors(node):
            if nbr in nodes and nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return seen == nodes

current_assignment = assignment.copy()
current_districts = {d: set(v) for d, v in districts.items()}
current_pops = district_pops.copy()
best_assignment = assignment.copy()
best_seats, _ = get_seat_count(current_assignment)
T_init = 1.0
T_final = 0.001
alpha = 0.995
T = T_init
max_iter = 2000

for iteration in range(max_iter):
    # Pick a random border VTD
    border_vtds = []
    for d, vtds in current_districts.items():
        for geoid in vtds:
            for nbr in graph.neighbors(geoid):
                nd = current_assignment.get(nbr)
                if nd is not None and nd != d:
                    border_vtds.append((geoid, d, nbr, nd))
    if not border_vtds:
        break
    geoid, d, nbr, nd = random.choice(border_vtds)
    pop = int(row_dict[geoid][POP_COL])
    # Only consider move if pop constraints are satisfied
    if current_pops[d] - pop < min_pop or current_pops[nd] + pop > max_pop:
        continue
    # Only move if both districts remain contiguous
    if not (is_contiguous(current_districts[d], remove_geoid=geoid) and is_contiguous(current_districts[nd], add_geoid=geoid)):
        continue
    # Try the move
    current_assignment[geoid] = nd
    current_districts[d].remove(geoid)
    current_districts[nd].add(geoid)
    current_pops[d] -= pop
    current_pops[nd] += pop
    new_seats, _ = get_seat_count(current_assignment)
    delta = new_seats - best_seats
    accept = False
    if delta > 0:
        accept = True
    else:
        # Simulated annealing: accept with probability exp(delta/T)
        if random.random() < math.exp(delta / max(T, 1e-6)):
            accept = True
    if accept:
        if new_seats > best_seats:
            best_assignment = current_assignment.copy()
            best_seats = new_seats
    else:
        # Revert
        current_assignment[geoid] = d
        current_districts[d].add(geoid)
        current_districts[nd].remove(geoid)
        current_pops[d] += pop
        current_pops[nd] -= pop
    if iteration % 100 == 0:
        print(f"Local search iteration {iteration}, best GOP seats: {best_seats}, T={T:.4f}")
    T = max(T * alpha, T_final)
assignment = best_assignment.copy()

# Save assignment
assign_df = pd.DataFrame(list(assignment.items()), columns=["GEOID20", "district"])
assign_df["GEOID20"] = assign_df["GEOID20"].astype(str)
assign_df.to_csv("district_assignment_contig_extreme.csv", index=False)
print("Contiguous extreme gerrymandered assignment saved to district_assignment_contig_extreme.csv")

# Summarize seats
merged["GEOID20"] = merged["GEOID20"].astype(str)
results = merged.merge(assign_df, on="GEOID20")
grouped = results.groupby("district").agg({REP_COL: "sum", DEM_COL: "sum"})
grouped["winner"] = grouped.apply(lambda row: "Republican" if row[REP_COL] > row[DEM_COL] else "Democrat", axis=1)
print("\nSeat counts by party:")
print(grouped["winner"].value_counts())
print("\nDistrict winners:")
print(grouped["winner"])
