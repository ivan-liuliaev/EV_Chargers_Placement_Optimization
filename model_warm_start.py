import pickle
import json
import gurobipy as gp
import time


def resolve_model_with_hyperparameters(model, cap_spot, max_chargers, chargers_budget_limit, previous_built_stations, area_demand):
    # Update MAX_CHARGERS
    for j in model.getVars():
        if j.VarName.startswith("build["):
            j.UB = max_chargers  # Update upper bound for chargers at each site
            site = int(j.VarName.split("[")[1].rstrip("]"))
            j.LB = previous_built_stations.get(site, 0)  # Set lower bound to previous built chargers
    
    # Do NOT update capacity constraints
    # Keep them as sum over served[i, j] <= build[i] * CAP_SPOT
    
    # Update budget limit
    model.getConstrByName("chargers_budget_limit").RHS = chargers_budget_limit

    # Apply warm start
    for var in model.getVars():
        if var.VarName.startswith("build["):
            site = int(var.VarName.split("[")[1].rstrip("]"))
            var.Start = previous_built_stations.get(site, 0)
    print("Warm start applied.")

    # ---------------------------- RESOLVE THE MODEL ---------------------------------------
    # Turn off Gurobi logging
    model.setParam('OutputFlag', 0)
    print(f"Resolving the model...")
    start_time = time.time()
    model.optimize()
    end_time = time.time()
    
    solving_time = end_time - start_time
    print(f"Solving time: {solving_time:.2f} seconds")

    # ---------------------------- OUTPUT RESULTS ------------------------------------------
    if model.status == gp.GRB.OPTIMAL:
        print("Optimal solution found. Calculating total demand coverage...")

        total_demand_coverage = 0
        total_demand = sum(area_demand.values())  # Total demand across all areas
        for var in model.getVars():
            if var.VarName.startswith("saturation_raw["):
                area_id = var.VarName.split("[")[1].rstrip("]")
                if area_id in area_demand:
                    coverage = min(var.X * area_demand[area_id], area_demand[area_id])
                    total_demand_coverage += coverage


        total_coverage_percentage = (total_demand_coverage / total_demand) * 100 if total_demand > 0 else 0
        print(f"Total Demand Coverage: {total_demand_coverage:.2f} ({total_coverage_percentage:.2f}%)")
        
        return {
            "total_demand_coverage": total_demand_coverage,
            "total_coverage_percentage": total_coverage_percentage,
            "objective": model.ObjVal
        }
    else:
        print("No optimal solution found.")
        return None





# Load the model once
model = gp.read("./data/model_output/saved_model.mps")
print("Model loaded successfully.")

# Load demand data and warm start data
with open("./data/georgia_processed_data/georgia_processed_data.pkl", "rb") as f:
    loaded_data = pickle.load(f)

c = loaded_data['areas_demand']  # Area demand
previous_built_stations = {}
try:
    with open("./data/model_output/built_stations.pkl", "rb") as f:
        previous_built_stations = pickle.load(f)
except FileNotFoundError:
    print("No previous solution found. Starting fresh.")

# Define hyperparameter combinations
# CHARGERS_BUDGET_LIMIT = 3500
# CAP_SPOT = 35294              
# MAX_CHARGERS = 60

budgets = range(3500, 3501, 100)
CAP_SPOT = 35294
MAX_CHARGERS = 60

# Placeholder for results
results = []

# Solve the model for each budget
for budget in budgets:
    print(f"\n--- Running for Budget = {budget} ---")
    result = resolve_model_with_hyperparameters(
        model=model,
        cap_spot=CAP_SPOT,
        max_chargers=MAX_CHARGERS,
        chargers_budget_limit=budget,
        previous_built_stations=previous_built_stations,
        area_demand=c,  # Pass demand data
    )
    if result:
        results.append({
            "budget": budget,
            "total_demand_coverage": result["total_demand_coverage"],
            "total_coverage_percentage": result["total_coverage_percentage"]
        })
        print(f"Accumulated Result: Budget={budget}, Total Demand Coverage={result['total_demand_coverage']:.2f}, "
              f"Percentage={result['total_coverage_percentage']:.2f}%")
    else:
        print(f"Failed to find optimal solution for Budget={budget}.")

# Export results to a JSON file
output_file = "./data/model_results_totals.json"
with open(output_file, "w") as f:
    json.dump(results, f, indent=4)

print(f"\nResults saved to {output_file}")