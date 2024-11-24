import pandas as pd

import gurobipy as gp
from gurobipy import Model, GRB, quicksum

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



# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- PARAMETERS ----------------------------------------------------
CHARGERS_BUDGET_LIMIT = 3500
CAP_SPOT = 35294              
MAX_CHARGERS = 60




# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- MODEL --------------------------------------------------------- 

# Create a new model
model = Model("EV Charging Station Placement with Charger Capacities")

# Decision variables
build = model.addVars(P, vtype=GRB.INTEGER, lb=0, ub=MAX_CHARGERS, name="build")  # Number of charging spots at each site
served = model.addVars(P, A, vtype=GRB.CONTINUOUS, lb=0, name="served")  # Trips served from site i to area j

# Auxiliary variables
z = model.addVars(A, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="z")  # Saturation level for each area
saturation_raw = model.addVars(A, vtype=GRB.CONTINUOUS, lb=0, name="saturation_raw") # Auxiliary variable for raw saturation calculation
is_built = model.addVars(P, vtype=GRB.BINARY, name="is_built") # Binary Auxiliary variable indicating whether a station is built at site j

# Objective: Maximize the total effective coverage across all areas
model.setObjective(quicksum(z[j] * c[j] for j in A), GRB.MAXIMIZE)

# Constraints
# Capacity constraint: Total trips served from site i to all areas cannot exceed the capacity from installed chargers
for i in P:
    model.addConstr(quicksum(served[i, j] for j in A) <= build[i] * CAP_SPOT, name=f"capacity_constraint_{i}")

# Prioritize local demand fulfillment for each station
for i in P:
    if i in A:  # Ensure the station `i` has its own area
        # Add binary variable to decide between demand and capacity
        is_capacity_limited = model.addVar(vtype=GRB.BINARY, name=f"is_capacity_limited_{i}")
        
        # If the station's capacity is smaller than the area's demand
        model.addConstr(served[i, i] <= build[i] * CAP_SPOT, name=f"local_capacity_limit_{i}")
        
        # If the area's demand is smaller, fulfill it entirely
        model.addConstr(served[i, i] <= c[i], name=f"local_demand_limit_{i}")
        
        # Logic for binary variable: either satisfy capacity or demand
        model.addConstr(
            served[i, i] == is_capacity_limited * (build[i] * CAP_SPOT) + (1 - is_capacity_limited) * c[i],
            name=f"local_demand_served_{i}"
        )

# Trip limit constraint: Trips served from site i to area j cannot exceed the actual trips
for i, j in tr:
    model.addConstr(served[i, j] <= tr[i, j], name=f"trip_limit_{i}_{j}")

# Raw saturation calculation for each area
for j in A:
    model.addConstr(saturation_raw[j] == quicksum(served[i, j] for i in P if (i, j) in tr) / c[j], name=f"saturation_raw_{j}")

# Link is_built[j] with build[j]: if build[j] > 0, then is_built[j] = 1
for j in P:
    model.addGenConstrIndicator(is_built[j], True, build[j] >= 1, name=f"is_built_{j}_linked")

# Saturation constraint: z[j] is the minimum of saturation_raw[j] and 1
for j in A:
    if j in P:  # If area j has a potential station site
        model.addGenConstrIndicator(is_built[j], True, z[j] == 1, name=f"station_is_in_the_area_{j}")
    model.addGenConstrMin(z[j], [saturation_raw[j], 1], name=f"min_constraint_{j}")

# Budget constraint: Limit the total number of chargers built across all sites to chargers_budget_limit
model.addConstr(quicksum(build[i] for i in P) <= CHARGERS_BUDGET_LIMIT, name="chargers_budget_limit")

# Optimize the model
model.optimize()




# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- OUTPUT PRINT --------------------------------------------------

# Display results in the requested format
if model.status == GRB.OPTIMAL:
    total_demand = sum(c[j] for j in A)
    total_demand_covered = sum(min(saturation_raw[j].x * c[j], c[j]) for j in A)
    total_demand_covered_percent = (total_demand_covered / total_demand) * 100 if total_demand > 0 else 0

    print(f"Total demand: {total_demand:.2f}")
    print(f"Total demand covered: {total_demand_covered:.2f}")
    print(f"Total demand covered (percent): {total_demand_covered_percent:.2f}%\n")

    fully_covered_areas = [j for j in A if saturation_raw[j].x >= 1]
    fully_covered_count = len(fully_covered_areas)
    fully_covered_total_demand = sum(c[j] for j in fully_covered_areas)
    fully_covered_mean_demand = fully_covered_total_demand / fully_covered_count if fully_covered_count > 0 else 0

    print(f"Fully covered areas:")
    print(f"  Count: {fully_covered_count}")
    print(f"  Mean area demand: {fully_covered_mean_demand:.2f}")
    print(f"  Total areas demand: {fully_covered_total_demand:.2f}\n")

    partially_covered_areas = [j for j in A if 0 < saturation_raw[j].x < 1]
    partially_covered_count = len(partially_covered_areas)
    partially_covered_total_demand = sum(c[j] for j in partially_covered_areas)
    partially_covered_demand_covered = sum(saturation_raw[j].x * c[j] for j in partially_covered_areas)
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

    not_covered_areas = [j for j in A if saturation_raw[j].x == 0]
    not_covered_count = len(not_covered_areas)
    not_covered_total_demand = sum(c[j] for j in not_covered_areas)
    not_covered_mean_demand = not_covered_total_demand / not_covered_count if not_covered_count > 0 else 0

    print(f"Areas not covered at all:")
    print(f"  Count: {not_covered_count}")
    print(f"  Mean area demand: {not_covered_mean_demand:.2f}")
    print(f"  Total areas demand: {not_covered_total_demand:.2f}")

else:
    print("No optimal solution found.")




# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- OUTPUT EXPORT -------------------------------------------------

# Extract data about stations built and chargers
if model.status == GRB.OPTIMAL:
    built_stations = {j: build[j].x for j in P if build[j].x > 0}  # Only include sites where chargers are built
    coverage_percentages = {j: saturation_raw[j].x * 100 for j in A}  # Calculate coverage as a percentage

    # Export built stations and chargers to a pickle file
    with open("./data/model_output/built_stations.pkl", "wb") as f:
        pickle.dump(built_stations, f)
    print(f"Exported built stations and chargers data to 'built_stations.pkl'.")

    # Export coverage percentages to a pickle file
    with open("./data/model_output/coverage_percentages.pkl", "wb") as f:
        pickle.dump(coverage_percentages, f)
    print(f"Exported coverage percentages to 'coverage_percentages.pkl'.")
else:
    print("No optimal solution found. Data not exported.")
