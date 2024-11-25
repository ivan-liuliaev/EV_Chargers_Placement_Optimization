import pickle
import json
import gurobipy as gp
import time


def resolve_model_with_hyperparameters(model, cap_spot, max_chargers, chargers_budget_limit, previous_built_stations, area_demand):

    model.reset()
    
    # Update MAX_CHARGERS
    for j in model.getVars():
        if j.VarName.startswith("build["):
            j.UB = max_chargers  # Update upper bound for chargers at each site
            site = int(j.VarName.split("[")[1].rstrip("]"))
            j.LB = previous_built_stations.get(site, 0)  # Set lower bound to previous built chargers


    # Update budget limit
    model.getConstrByName("chargers_budget_limit").RHS = chargers_budget_limit

    # Ensure updates are applied
    model.update()

    # Apply warm start
    for var in model.getVars():
        if var.VarName.startswith("build["):
            site = int(var.VarName.split("[")[1].rstrip("]"))
            var.Start = previous_built_stations.get(site, 0)
    print("Warm start applied.")

    # Update the model to apply changes
    model.update()

    # ---------------------------- RESOLVE THE MODEL ---------------------------------------
    # Turn off Gurobi logging
    model.setParam('OutputFlag', 0)

    # Stop at objective confidence interval of 5%
    model.setParam('MIPGap', 0.05)
    model.setParam('TimeLimit', 200)  # Stop after 200 seconds
    
    print(f"Resolving the model...")
    start_time = time.time()
    model.optimize()
    end_time = time.time()
    
    solving_time = end_time - start_time
    print(f"Solving time: {solving_time:.2f} seconds")

    # ---------------------------- OUTPUT RESULTS ------------------------------------------
    if model.status in [gp.GRB.OPTIMAL, gp.GRB.SUBOPTIMAL]:
        print(f"Solution found with gap: {model.MIPGap * 100:.2f}%")
        print(f"Objective value: {model.ObjVal}")

        print("Parameters given:")
        print("CHARGERS_BUDGET_LIMIT:", chargers_budget_limit)
        print("CAP_SPOT:", cap_spot)
        print("MAX_CHARGERS:", max_chargers)

        budget_constraint = model.getConstrByName("chargers_budget_limit")
        slack = budget_constraint.Slack
        print(f"Budget constraint slack: {slack}")

        total_demand_coverage = 0
        total_demand = sum(area_demand.values())  # Total demand across all areas
        for var in model.getVars():
            if var.VarName.startswith("saturation_raw["):
                area_id = var.VarName.split("[")[1].rstrip("]")
                if area_id in area_demand:
                    coverage = min(var.X * area_demand[area_id], area_demand[area_id])
                    total_demand_coverage += coverage


        total_coverage_percentage = (total_demand_coverage / total_demand) * 100 if total_demand > 0 else 0
        print(f"Total Demand Coverage (in Millions): {total_demand_coverage/MILLION:.2f}")
        print(f"Total Demand Coverage Percentage: \033[1;31m{total_coverage_percentage:.2f}%\033[0m")

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
tr = loaded_data['trips']
P = loaded_data['potential_sites']
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

MILLION = 1000000
BUDGET = 100 * MILLION
COST = 300000 # of a charger

budgets = range(10, 50, 10) # in millions of $
# budgets = [10, 3000, 4500] # in millions of $
# charger_amounts = [int(budget * MILLION / COST) for budget in budgets]
charger_amounts = [1, 10, 250, 500, 550, 600, 650]
# charger_amounts = range(200, 1000, 500)

# CHARGERS_BUDGET_LIMIT = 1500
# CAP_SPOT = 400000        # DOESNT UPDATE!!!    I removed the code  , only updates when model.py updates it
MAX_CHARGERS = 10

# Placeholder for results
results = []

# Solve the model for each budget
for charger_amount_budget in charger_amounts:
    print(f"\n--- Running for Budget (in millions of $) = {charger_amount_budget * COST / MILLION} ---")
    print(f"--- Chargers: {charger_amount_budget} ---")

    model.reset()
    result = resolve_model_with_hyperparameters(
        model=model,
        cap_spot=CAP_SPOT,
        max_chargers=MAX_CHARGERS,
        chargers_budget_limit=charger_amount_budget,
        previous_built_stations=previous_built_stations,
        area_demand=c
    )

    if result:
        results.append({
            "budget": charger_amount_budget,
            "total_demand_coverage": result["total_demand_coverage"],
            "total_coverage_percentage": result["total_coverage_percentage"]
        })
        print(f"Accumulated Result: Budget={charger_amount_budget}, Total Demand Coverage={result['total_demand_coverage']:.2f}, "
              f"Percentage={result['total_coverage_percentage']:.2f}%")
    else:
        print(f"Failed to find optimal solution for Budget={charger_amount_budget}.")

# Export results to a JSON file
output_file = "./data/model_results_totals.json"
with open(output_file, "w") as f:
    json.dump(results, f, indent=4)

print(f"\nResults saved to {output_file}")