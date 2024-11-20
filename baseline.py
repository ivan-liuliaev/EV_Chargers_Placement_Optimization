import pandas as pd

from synthetic_data_gen import GENERATE_DATA
import pickle

# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- DATA ----------------------------------------------------------

# ---------------------------- SYNTHETIC -----------------------------------------------------
# N_AREAS = 10
# N_POTENTIAL_SITES = 5
# CHARGERS_BUDGET_LIMIT = 15
# CAP_SPOT = 200        # Each charging spot serves up to 200 trips
# MAX_CHARGERS = 5

# A, P, c, tr = GENERATE_DATA(
#     N_AREAS,
#     N_POTENTIAL_SITES,
#     CHARGERS_BUDGET_LIMIT,
#     CAP_SPOT,
#     MAX_CHARGERS,
#     SEED = 43
# )


# ---------------------------- GEORGIA DATA -----------------------------------------------------
# CODE TO IMPORT
# Load the data from the .pkl file
with open("./data/georgia_processed_data/georgia_processed_data.pkl", "rb") as f:
    loaded_data = pickle.load(f)

print(loaded_data.keys())
A = loaded_data['areas']
P = loaded_data['potential_sites']
c = loaded_data['areas_demand']
tr = loaded_data['trips']

CHARGERS_BUDGET_LIMIT = 3500
CAP_SPOT = 35294              
MAX_CHARGERS = 60


# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- MODEL --------------------------------------------------------- 


# Step 1: Aggregate total outgoing traffic per potential site
site_traffic = {site: 0 for site in P}
for (site, area), trips in tr.items():
    site_traffic[site] += trips

# Step 2: Sort sites by total traffic in descending order
sorted_sites = sorted(site_traffic.items(), key=lambda x: x[1], reverse=True)

# Step 3: Allocate chargers to the busiest sites, constrained by budget and capacity
remaining_budget = CHARGERS_BUDGET_LIMIT
site_chargers = {site: 0 for site in P}
area_served_trips = {area: 0 for area in A}

for site, _ in sorted_sites:
    if remaining_budget == 0:
        break

    # Maximum chargers that can be utilized at this site
    max_utilizable = sum(tr[site, area] for area in A if (site, area) in tr) // CAP_SPOT
    chargers_to_place = min(max_utilizable, MAX_CHARGERS, remaining_budget)
    site_chargers[site] = chargers_to_place
    remaining_budget -= chargers_to_place

    # Distribute the capacity to areas with the most trips
    for area in sorted(A, key=lambda a: tr.get((site, a), 0), reverse=True):
        if (site, area) in tr:
            trips_served = min(tr[site, area], chargers_to_place * CAP_SPOT - area_served_trips[area])
            area_served_trips[area] += trips_served

# Calculate overall demand coverage
total_demand = sum(c[area] for area in A)
demand_covered = sum(min(area_served_trips[area], c[area]) for area in A)
coverage_percent = (demand_covered / total_demand) * 100 if total_demand > 0 else 0




# Display results in the requested format
total_demand = sum(c[j] for j in A)
demand_covered = sum(min(area_served_trips[j], c[j]) for j in A)
total_demand_covered_percent = (demand_covered / total_demand) * 100 if total_demand > 0 else 0

print(f"Total demand: {total_demand:.2f}")
print(f"Total demand covered: {demand_covered:.2f}")
print(f"Total demand covered (percent): {total_demand_covered_percent:.2f}%\n")

# Fully covered areas
fully_covered_areas = [j for j in A if area_served_trips[j] >= c[j]]
fully_covered_count = len(fully_covered_areas)
fully_covered_total_demand = sum(c[j] for j in fully_covered_areas)
fully_covered_mean_demand = fully_covered_total_demand / fully_covered_count if fully_covered_count > 0 else 0

print(f"Fully covered areas:")
print(f"  Count: {fully_covered_count}")
print(f"  Mean area demand: {fully_covered_mean_demand:.2f}")
print(f"  Total areas demand: {fully_covered_total_demand:.2f}\n")

# Partially covered areas
partially_covered_areas = [j for j in A if 0 < area_served_trips[j] < c[j]]
partially_covered_count = len(partially_covered_areas)
partially_covered_total_demand = sum(c[j] for j in partially_covered_areas)
partially_covered_demand_covered = sum(area_served_trips[j] for j in partially_covered_areas)
partially_covered_mean_demand = (
    partially_covered_total_demand / partially_covered_count if partially_covered_count > 0 else 0
)
partially_covered_mean_demand_covered = (
    partially_covered_demand_covered / partially_covered_count if partially_covered_count > 0 else 0
)

print(f"Partially covered areas:")
print(f"  Count: {partially_covered_count}")
print(f"  Mean area demand (including demand not covered): {partially_covered_mean_demand:.2f}")
print(f"  Mean area demand covered: {partially_covered_mean_demand_covered:.2f}")
print(f"  Total areas demand covered: {partially_covered_demand_covered:.2f}")
print(f"  Total areas demand (including demand not covered): {partially_covered_total_demand:.2f}\n")

# Not covered areas
not_covered_areas = [j for j in A if area_served_trips[j] == 0]
not_covered_count = len(not_covered_areas)
not_covered_total_demand = sum(c[j] for j in not_covered_areas)
not_covered_mean_demand = not_covered_total_demand / not_covered_count if not_covered_count > 0 else 0

print(f"Areas not covered at all:")
print(f"  Count: {not_covered_count}")
print(f"  Mean area demand: {not_covered_mean_demand:.2f}")
print(f"  Total areas demand: {not_covered_total_demand:.2f}")
