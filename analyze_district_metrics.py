import pandas as pd
import numpy as np

# Load data
CSV_PATH = 'fl_2020_vtd.csv'
df = pd.read_csv(CSV_PATH)

# Ensure numeric fields are parsed correctly
def coerce_numeric(df):
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass
    return df

df = coerce_numeric(df)

# Placeholder for number of districts (update as needed)
NUM_DISTRICTS = 28

# --- Population balance ---
# Compute total population and ideal district population
total_pop = df['pop'].sum()
ideal_pop = total_pop / NUM_DISTRICTS


# --- Population balance metrics ---
# Assumes a 'district' column exists in the dataframe
if 'district' in df.columns:
    district_pops = df.groupby('district')['pop'].sum()
    deviations = (district_pops - ideal_pop).abs() / ideal_pop
    pop_balance_summary = pd.DataFrame({
        'district_pop': district_pops,
        'deviation': deviations
    })
else:
    pop_balance_summary = None
    print("Warning: No 'district' column found. Cannot compute population balance metrics.")

# --- Community integrity metrics ---
# TODO: Compute county/VTD splits, homogeneity index, opportunity districts

# --- Competitiveness metrics ---
# TODO: Compute two-party share, margin of victory, competitive districts, mean–median, efficiency gap

# --- Output summary ---
# TODO: Print or return structured summary

if __name__ == '__main__':
    print(f'Total population: {total_pop}')
    print(f'Ideal district population: {ideal_pop:.2f}')
    if pop_balance_summary is not None:
        print("\nPopulation balance by district:")
        print(pop_balance_summary)
        print("\nMax deviation: {:.4f}".format(pop_balance_summary['deviation'].max()))
        print("Mean deviation: {:.4f}".format(pop_balance_summary['deviation'].mean()))
    else:
        print("Population balance metrics not available.")
