import pandas as pd
import pickle

# -------------------------------------------------------------------------------------------- 
# ---------------------------- DATA ----------------------------------------------------------

# Load the data from the .pkl file
with open("./data/georgia_processed_data/georgia_processed_data.pkl", "rb") as f:
    loaded_data = pickle.load(f)

A = loaded_data['areas']
P = loaded_data['potential_sites']
c = loaded_data['areas_demand']
tr = loaded_data['trips']

# -------------------------------------------------------------------------------------------- 
# ---------------------------- PARAMETERS ----------------------------------------------------

MILLION = 1_000_000
BUDGET = 80 * MILLION       # Total budget
STATION_COST = 25_000      # $250k per station
CHARGER_COST = 5_000       # $50k per charger
CAP_SPOT = 50_000          # Each charging spot serves up to 500,000 trips
MAX_CHARGERS = 30           # Maximum chargers per station

# Calculate maximum number of stations and chargers we can build within the budget
MAX_STATIONS = BUDGET // (STATION_COST + CHARGER_COST)
CHARGERS_BUDGET_LIMIT = int(BUDGET // (STATION_COST + CHARGER_COST))  # Maximum chargers considering at least one charger per station

# -------------------------------------------------------------------------------------------- 
# ---------------------------- HEURISTIC ALGORITHM ------------------------------------------- 

# Step 1: Aggregate total outgoing traffic per potential site
site_total_demand = {site: 0 for site in P}
for (site, area), trips in tr.items():
    site_total_demand[site] += trips

# Step 2: Sort sites by total traffic in descending order
sorted_sites = sorted(site_total_demand.items(), key=lambda x: x[1], reverse=True)

# Step 3: Allocate chargers to the busiest sites within budget and capacity constraints
remaining_budget = BUDGET
site_chargers = {site: 0 for site in P}
area_served_trips = {area: 0 for area in A}

for site, total_trips in sorted_sites:
    if remaining_budget < (STATION_COST + CHARGER_COST):
        break  # Not enough budget to build more stations with at least one charger

    # Calculate the maximum number of chargers we can install at this site
    max_chargers_site = min(MAX_CHARGERS, remaining_budget // CHARGER_COST)
    max_utilizable_chargers = min(
        (site_total_demand[site] // CAP_SPOT) + 1,  # +1 to cover partial capacity
        max_chargers_site
    )

    # Allocate at least one charger if possible
    chargers_to_place = max(1, int(max_utilizable_chargers))

    # Update budget
    total_station_cost = STATION_COST + (chargers_to_place * CHARGER_COST)
    if total_station_cost > remaining_budget:
        chargers_to_place = (remaining_budget - STATION_COST) // CHARGER_COST
        if chargers_to_place < 1:
            break  # Cannot afford to build more stations
        total_station_cost = STATION_COST + (chargers_to_place * CHARGER_COST)

    remaining_budget -= total_station_cost
    site_chargers[site] = chargers_to_place

    # Distribute the capacity to areas proportionally based on trips
    site_area_trips = {area: tr.get((site, area), 0) for area in A}
    total_site_area_trips = sum(site_area_trips.values())

    for area, trips in site_area_trips.items():
        if trips > 0 and area_served_trips[area] < c[area]:
            # Proportion of site's capacity allocated to this area
            proportion = trips / total_site_area_trips
            capacity = chargers_to_place * CAP_SPOT * proportion
            trips_served = min(capacity, c[area] - area_served_trips[area])
            area_served_trips[area] += trips_served

# Calculate overall demand coverage
total_demand = sum(c[area] for area in A)
demand_covered = sum(min(area_served_trips[area], c[area]) for area in A)
coverage_percent = (demand_covered / total_demand) * 100 if total_demand > 0 else 0

# -------------------------------------------------------------------------------------------- 
# ---------------------------- OUTPUT PRINT --------------------------------------------------

print(f"Total demand (in MM): {total_demand / 1_000_000:.2f}")
print(f"Total demand covered (in MM): {demand_covered / 1_000_000:.2f}")
print(f"Total Demand Coverage Percentage: \033[1;31m{coverage_percent:.2f}%\033[0m\n")
print("Parameters given:")
print(f"BUDGET: {BUDGET}")
print(f"STATION_COST: {STATION_COST}")
print(f"CHARGER_COST: {CHARGER_COST}")
print(f"CAP_SPOT: {CAP_SPOT}")
print(f"MAX_CHARGERS: {MAX_CHARGERS}")

# Fully covered areas
fully_covered_areas = [area for area in A if area_served_trips[area] >= c[area]]
fully_covered_count = len(fully_covered_areas)
fully_covered_total_demand = sum(c[area] for area in fully_covered_areas)
fully_covered_mean_demand = fully_covered_total_demand / fully_covered_count if fully_covered_count > 0 else 0

print(f"\nFully covered areas:")
print(f"  Count: {fully_covered_count}")
print(f"  Mean area demand: {fully_covered_mean_demand:.2f}")
print(f"  Total areas demand: {fully_covered_total_demand:.2f}")

# Partially covered areas
partially_covered_areas = [area for area in A if 0 < area_served_trips[area] < c[area]]
partially_covered_count = len(partially_covered_areas)
partially_covered_total_demand = sum(c[area] for area in partially_covered_areas)
partially_covered_demand_covered = sum(area_served_trips[area] for area in partially_covered_areas)
partially_covered_mean_demand = (
    partially_covered_total_demand / partially_covered_count if partially_covered_count > 0 else 0
)
partially_covered_mean_demand_covered = (
    partially_covered_demand_covered / partially_covered_count if partially_covered_count > 0 else 0
)

print(f"\nPartially covered areas:")
print(f"  Count: {partially_covered_count}")
print(f"  Mean area demand (including demand not covered): {partially_covered_mean_demand:.2f}")
print(f"  Mean area demand covered: {partially_covered_mean_demand_covered:.2f}")
print(f"  Total areas demand covered: {partially_covered_demand_covered:.2f}")
print(f"  Total areas demand (including demand not covered): {partially_covered_total_demand:.2f}")

# Not covered areas
not_covered_areas = [area for area in A if area_served_trips[area] == 0]
not_covered_count = len(not_covered_areas)
not_covered_total_demand = sum(c[area] for area in not_covered_areas)
not_covered_mean_demand = not_covered_total_demand / not_covered_count if not_covered_count > 0 else 0

print(f"\nAreas not covered at all:")
print(f"  Count: {not_covered_count}")
print(f"  Mean area demand: {not_covered_mean_demand:.2f}")
print(f"  Total areas demand: {not_covered_total_demand:.2f}")

# Additional Output: Total number of stations and chargers built
total_chargers_built = sum(site_chargers[site] for site in P)
stations_built = len([site for site in P if site_chargers[site] >= 1])

print(f"\nTotal number of stations built: {stations_built}")
print(f"Total number of chargers built: {total_chargers_built}")
print(f"Remaining budget: {remaining_budget}")
