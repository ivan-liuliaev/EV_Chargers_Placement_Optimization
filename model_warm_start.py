import pickle
import gurobipy as gp
from gurobipy import Model, GRB, quicksum

# ---------------------------- LOAD PREVIOUS SOLUTION ---------------------------------
try:
    with open("./data/model_output/built_stations.pkl", "rb") as f:
        previous_built_stations = pickle.load(f)
    print("Loaded previous solution for warm start.")
except FileNotFoundError:
    print("Previous solution not found. Starting without warm start.")
    previous_built_stations = {}

# ---------------------------- LOAD MODEL ---------------------------------------------

try:
    # Load the saved model
    model = gp.read("./data/model_output/saved_model.mps")
    print("Model loaded successfully.")
except FileNotFoundError:
    print("Saved model not found. Ensure the model has been saved.")
    raise

# ---------------------------- APPLY WARM START ----------------------------------------

# Load additional data if needed (e.g., trips, demand, etc.)
with open("./data/georgia_processed_data/georgia_processed_data.pkl", "rb") as f:
    loaded_data = pickle.load(f)

A = loaded_data['areas']
P = loaded_data['potential_sites']
c = loaded_data['areas_demand']
tr = loaded_data['trips']



# ---------------------------- TWEAK PARAMETERS ---------------------------------------
# CHARGERS_BUDGET_LIMIT = 3500
# CAP_SPOT = 35294              
# MAX_CHARGERS = 60


# Updated parameters
CAP_SPOT = 350000  
MAX_CHARGERS = 50 
CHARGERS_BUDGET_LIMIT = 500  

# Update bounds for `build` variables (MAX_CHARGERS)
for j in P:
    var = model.getVarByName(f"build[{j}]")
    if var:
        var.UB = MAX_CHARGERS  # Update upper bound for chargers at each site

# Update capacity constraints (CAP_SPOT)
for i in P:
    constr = model.getConstrByName(f"capacity_constraint_{i}")
    if constr:
        # Modify the right-hand side of the capacity constraint
        constr.RHS = CAP_SPOT * model.getVarByName(f"build[{i}]").Start if f"build[{i}]" in previous_built_stations else CAP_SPOT


# Update the budget limit or any other constraints
model.getConstrByName("chargers_budget_limit").RHS = CHARGERS_BUDGET_LIMIT



# ---------------------------- APPLY WARM START ----------------------------------------

# Apply warm start: Set initial values based on the previous solution
for j in P:
    # Warm start for station builds
    var = model.getVarByName(f"build[{j}]")
    if var:
        var.Start = previous_built_stations.get(j, 0)  # Use previous solution or default to 0

for (i, j) in tr:
    # Warm start for trips served
    var = model.getVarByName(f"served[{i},{j}]")
    if var and i in previous_built_stations:
        var.Start = min(tr[i, j], previous_built_stations.get(i, 0) * 35294)  # Adjust for capacity
    elif var:
        var.Start = 0

# ---------------------------- RESOLVE THE MODEL ---------------------------------------

print(f"Resolving the model with a new budget limit: {CHARGERS_BUDGET_LIMIT}")
model.optimize()

# ---------------------------- OUTPUT RESULTS ------------------------------------------

if model.status == GRB.OPTIMAL:
    print("Resolved Model Results:")
    total_demand = sum(c[j] for j in A)
    total_demand_covered = sum(
        min(model.getVarByName(f"saturation_raw[{j}]").X * c[j], c[j]) for j in A
    )
    total_demand_covered_percent = (total_demand_covered / total_demand) * 100 if total_demand > 0 else 0

    print(f"Total demand: {total_demand:.2f}")
    print(f"Total demand covered: {total_demand_covered:.2f}")
    print(f"Total demand covered (percent): {total_demand_covered_percent:.2f}%\n")

    # Export the updated results
    built_stations = {j: model.getVarByName(f"build[{j}]").X for j in P if model.getVarByName(f"build[{j}]").X > 0}
    coverage_percentages = {
        j: model.getVarByName(f"saturation_raw[{j}]").X * 100 for j in A
    }

    with open("./data/model_output/built_stations.pkl", "wb") as f:
        pickle.dump(built_stations, f)
    print(f"Updated built stations and chargers data exported to 'built_stations.pkl'.")

    with open("./data/model_output/coverage_percentages.pkl", "wb") as f:
        pickle.dump(coverage_percentages, f)
    print(f"Updated coverage percentages exported to 'coverage_percentages.pkl'.")
else:
    print("No optimal solution found after resolving.")
