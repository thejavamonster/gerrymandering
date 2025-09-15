import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# Load merged VTDs and district assignment
merged = gpd.read_file("merged_vtds.shp")
districts = pd.read_csv("district_assignment.csv")

# Merge assignment into GeoDataFrame
merged = merged.merge(districts, on="GEOID20")

# Plot districts colored by assignment
fig, ax = plt.subplots(1, 1, figsize=(12, 12))
merged.plot(column="district", cmap="tab20", linewidth=0.1, edgecolor="black", ax=ax, legend=True)
plt.title("Gerrymandered Florida Districts")
plt.axis("off")
plt.tight_layout()
plt.savefig("gerrymandered_districts.png", dpi=300)
plt.show()

# Compute and print partisan seat count
merged["rep_win"] = merged["pre_20_rep_tru"] > merged["pre_20_dem_bid"]
seat_count = merged.groupby("district")["rep_win"].sum().sum()
print(f"Number of districts won by target party: {seat_count}")
