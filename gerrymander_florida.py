from gerrychain import (GeographicPartition, Partition, MarkovChain, proposals, constraints, accept)
from gerrychain.updaters import Tally
import networkx as nx
import geopandas as gpd
import random
from gerrychain.tree import recursive_tree_part

# Load graph and merged data
import pickle
with open("vtd_graph.gpickle", "rb") as f:
    graph = pickle.load(f)
merged = gpd.read_file("merged_vtds.shp")

# Number of districts (set as needed)
NUM_DISTRICTS = 27  # Example: Florida congressional
POP_COL = "population"


# Ensure graph is connected; use largest connected component if not
import networkx as nx
if not nx.is_connected(graph):
    largest_cc = max(nx.connected_components(graph), key=len)
    graph = graph.subgraph(largest_cc).copy()

# Calculate ideal population per district
ideal_pop = sum(graph.nodes[n][POP_COL] for n in graph.nodes) / NUM_DISTRICTS

# Use recursive_tree_part to generate a valid initial assignment
assignment = recursive_tree_part(
    graph,
    parts=list(range(NUM_DISTRICTS)),
    pop_col=POP_COL,
    pop_target=ideal_pop,
    epsilon=0.20,  # 20% deviation, can tighten later
    node_repeats=1
)


# Build initial partition using Tally updaters
partition = GeographicPartition(
    graph,
    assignment,
    updaters={
        "population": Tally(POP_COL, alias="population"),
        "dem": Tally("dem", alias="dem"),
        "rep": Tally("rep", alias="rep"),
    },
)


# Population constraint: districts within 20% of ideal
pop_constraint = constraints.within_percent_of_ideal_population(partition, 0.20)

# Objective: maximize number of districts with rep > dem

def seat_count(partition):
    count = 0
    for part in partition.parts:
        rep = sum(graph.nodes[n]["rep"] for n in partition.parts[part])
        dem = sum(graph.nodes[n]["dem"] for n in partition.parts[part])
        if dem > rep:  # Optimize for Democrats
            count += 1
    return count

# Set up MarkovChain with ReCom proposal
chain = MarkovChain(
    proposal=lambda partition: proposals.recom(
        partition,
        pop_col=POP_COL,
        pop_target=ideal_pop,
        epsilon=0.20
    ),
    constraints=[pop_constraint],
    accept=accept.always_accept,
    initial_state=partition,
    total_steps=100
)

# Run chain and save best plan
best_partition = None
best_seats = -1
for step, part in enumerate(chain):
    seats = seat_count(part)
    if seats > best_seats:
        best_seats = seats
        best_partition = part
    print(f"Step {step}: {seats} seats for target party")

# Save best assignment
district_assignment = {node: best_partition.assignment[node] for node in best_partition.graph.nodes}
import pandas as pd
assign_df = pd.DataFrame(list(district_assignment.items()), columns=["GEOID20", "district"])
assign_df.to_csv("district_assignment.csv", index=False)
print("Best district assignment saved to district_assignment.csv")
