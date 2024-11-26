import pickle
import json
import gurobipy as gp
import time

def resolve_model_with_hyperparameters(model, cap_spot, max_chargers, budget, previous_built_stations, area_demand, station_cost, charger_cost):

    model.reset()
    
    # Update MAX_CHARGERS and apply warm start for 'build' variables
    for var in model.getVars():
        if var.VarName.startswith("build["):
            site = int(var.VarName.split("[")[1].rstrip("]"))
            var.UB = max_chargers  # Update upper bound for chargers at each site
            var.LB = previous_built_stations.get(site, 0)  # Set lower bound to previous built chargers
            var.Start = previous_built_stations.get(site, 0)  # Warm start for 'build' variables

    # Apply warm start for 'is_built' variables
    for var in model.getVars():
        if var.VarName.startswith("is_built["):
            site = int(var.VarName.split("[")[1].rstrip("]"))
            var.Start = 1 if previous_built_stations.get(site, 0) > 0 else 0

    print("Warm start applied.")

    # Update budget constraint RHS
    budget_constraint = model.getConstrByName("budget_constraint")
    budget_constraint.RHS = budget

    # Ensure updates are applied
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
        print("BUDGET:", budget)
        print("STATION_COST:", station_cost)
        print("CHARGER_COST:", charger_cost)
        # print("CAP_SPOT:", cap_spot)
        print("MAX_CHARGERS:", max_chargers)

        budget_constraint = model.getConstrByName("budget_constraint")
        slack = budget_constraint.Slack
        total_cost_used = budget - slack
        print(f"Total cost used: {total_cost_used}")
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
            "objective": model.ObjVal,
            "total_cost_used": total_cost_used
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
MILLION = 1000000
STATION_COST = 250000 # CAP_SPOT does not update automoatically, only after model.py rerun
CHARGER_COST = 50000 # CAP_SPOT does not update automoatically, only after model.py rerun

budgets = range(4 * MILLION, 41 * MILLION, 4 * MILLION)  # Budgets in dollars
# Convert budgets to list
budgets = list(budgets)

CAP_SPOT = 50000  # CAP_SPOT does not update automoatically, only after model.py rerun
MAX_CHARGERS = 30  # Update MAX_CHARGERS if necessary

# Placeholder for results
results = []

# Solve the model for each budget
for budget in budgets:
    print(f"\n--- Running for Budget (in millions of $) = {budget / MILLION} ---")

    model.reset()
    result = resolve_model_with_hyperparameters(
        model=model,
        cap_spot=CAP_SPOT,
        max_chargers=MAX_CHARGERS,
        budget=budget,
        previous_built_stations=previous_built_stations,
        area_demand=c,
        station_cost=STATION_COST,
        charger_cost=CHARGER_COST
    )

    if result:
        results.append({
            "budget": budget,
            "total_cost_used": result["total_cost_used"],
            "total_demand_coverage": result["total_demand_coverage"],
            "total_coverage_percentage": result["total_coverage_percentage"]
        })
        print(f"Accumulated Result: Budget={budget / MILLION}M, Total Demand Coverage={result['total_demand_coverage']:.2f}, "
              f"Percentage={result['total_coverage_percentage']:.2f}%")
    else:
        print(f"Failed to find optimal solution for Budget={budget / MILLION}M.")

# Export results to a JSON file
output_file = "./data/model_results_totals.json"
with open(output_file, "w") as f:
    json.dump(results, f, indent=4)

print(f"\nResults saved to {output_file}")
