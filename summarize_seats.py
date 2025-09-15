import pandas as pd
import geopandas as gpd

# Load merged VTDs and district assignment
merged = gpd.read_file("merged_vtds.shp")
districts = pd.read_csv("district_assignment.csv")

# Merge assignment into GeoDataFrame
merged = merged.merge(districts, on="GEOID20")


# Sum up votes by district using correct columns
results = merged.groupby("district").agg({
	"pre_20_rep": "sum",
	"pre_20_dem": "sum"
})

# Determine winner for each district
results["winner"] = results.apply(lambda row: "Republican" if row["pre_20_rep"] > row["pre_20_dem"] else "Democrat", axis=1)

# Count seats for each party
seat_counts = results["winner"].value_counts()
print("Seat counts by party:")
print(seat_counts)

# Optionally, print the winner for each district
print("\nDistrict winners:")
print(results["winner"])
