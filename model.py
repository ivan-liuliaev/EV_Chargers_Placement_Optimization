import gurobipy as gp
from gurobipy import Model, GRB, quicksum
import pandas as pd
import random


# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- DATA GENERATION -----------------------------------------------
# Parameters
N_AREAS = 10
N_POTENTIAL_SITES = 5

# Define areas
A = [f"Area{i}" for i in range(1, N_AREAS + 1)]  # 20 areas

# Randomly select potential sites from areas
P = random.sample(A, N_POTENTIAL_SITES)  # 10 areas as potential sites

# Define hubs and residential areas
# Assume first half of P are hubs and second half are residential areas
hubs = A[:N_AREAS // 2]
residential_areas = A[N_AREAS // 2:]

# Generate trips based on area types
tr = {}
for i in P:
    for j in A:
        if i in hubs:
            # Hubs receive higher inbound trips from residential areas
            if j in residential_areas:
                tr[(i, j)] = random.randint(800, 1200)
            else:
                tr[(i, j)] = random.randint(700, 1100)
        elif i in residential_areas:
            # Residential areas have higher outbound trips to hubs
            if j in hubs:
                tr[(i, j)] = random.randint(800, 1200)
            else:
                tr[(i, j)] = random.randint(150, 300)

# Random capacities for each area (higher for residential areas)
c = {}
for j in A:
    if j in residential_areas:
        c[j] = random.randint(800, 1000)  # Higher population for residential areas
    else:
        c[j] = random.randint(100, 200)  # Lower population for hubs



# Convert the trips dictionary `tr` to a DataFrame
tr_matrix = pd.DataFrame(0, index=sorted(P), columns=A)  # Initialize with zeros

# Populate the DataFrame with trip values
for (i, j), value in tr.items():
    tr_matrix.loc[i, j] = value

# Display trips matrix
print("\nTrips Matrix (Potential Station Sites as rows, Areas as columns):")
print(tr_matrix)

# Convert capacities dictionary `c` to a DataFrame
c_df = pd.DataFrame.from_dict(c, orient='index', columns=['Capacity'])

# Display capacities matrix
print("\nArea Capacities (c):")
print(c_df.T)  # Transpose for a row-style display


CHARGERS_BUDGET_LIMIT = 15
CAP_SPOT = 200  # Each charging spot serves up to 150 trips
MAX_CHARGERS = 5  # Maximum number of chargers per site
# Constants for the model
print("\nConstants:")
print("cap_spot:", CAP_SPOT)
print("max_chargers:", MAX_CHARGERS)
print("chargers_budget_limit:", CHARGERS_BUDGET_LIMIT)




# -------------------------------------------------------------------------------------------- 
# -------------------------------------------------------------------------------------------- 
# ---------------------------- MODEL --------------------------------------------------------- 

# Create a new model
model = Model("EV Charging Station Placement with Charger Capacities")

# Decision variables
build = model.addVars(P, vtype=GRB.INTEGER, lb=0, ub=MAX_CHARGERS, name="build")  # Number of charging spots at each site
served = model.addVars(P, A, vtype=GRB.CONTINUOUS, lb=0, name="served")  # Trips served from site i to area j
z = model.addVars(A, vtype=GRB.CONTINUOUS, lb=0, ub=1, name="z")  # Saturation level for each area

# Auxiliary variable for raw saturation calculation
saturation_raw = model.addVars(A, vtype=GRB.CONTINUOUS, lb=0, name="saturation_raw")

# Objective: Maximize the total effective coverage across all areas
model.setObjective(quicksum(z[j] * c[j] for j in A), GRB.MAXIMIZE)


# Constraints
# Capacity constraint: Total trips served from site i to all areas cannot exceed the capacity from installed chargers
for i in P:
    model.addConstr(quicksum(served[i, j] for j in A) <= build[i] * CAP_SPOT, name=f"capacity_constraint_{i}")



# Trip limit constraint: Trips served from site i to area j cannot exceed the actual trips
for i, j in tr:
    model.addConstr(served[i, j] <= tr[i, j], name=f"trip_limit_{i}_{j}")



# Raw saturation calculation for each area
for j in A:
    model.addConstr(saturation_raw[j] == quicksum(served[i, j] for i in P if (i, j) in tr) / c[j], name=f"saturation_raw_{j}")



# Saturation calculation: z[j] is the minimum of 1 and saturation_raw[j]
for j in A:
    model.addGenConstrMin(z[j], [saturation_raw[j], 1], name=f"saturation_{j}")

# New constraint: Limit the total number of chargers built across all sites to chargers_budget_limit
model.addConstr(quicksum(build[i] for i in P) <= CHARGERS_BUDGET_LIMIT, name="chargers_budget_limit")

# Optimize the model
model.optimize()

# Display results
if model.status == GRB.OPTIMAL:
    print("Optimal solution found:")
    for i in P:
        if build[i].x > 0.5:
            print(f"Build {int(build[i].x)} charging spots at site {i}")
    for j in A:
        a = 1
        print(f"Effective coverage for area {j}: {z[j].x * 100:.2f}% of capacity")

else:
    print("No optimal solution found.")