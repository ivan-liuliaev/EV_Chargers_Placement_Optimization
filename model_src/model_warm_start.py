import pandas as pd
import gurobipy as gp
from gurobipy import Model, GRB, quicksum
import pickle
import json
import time

def resolve_model_with_hyperparameters(
    model,
    cap_spot,
    max_chargers,
    budget,
    previous_built_stations,
    area_demand,
    station_cost,
    charger_cost
):
    """
    Resolves the Gurobi model with updated hyperparameters and warm starts.

    Parameters:
    - model: Gurobi model object.
    - cap_spot: Capacity per charger.
    - max_chargers: Maximum number of chargers per station.
    - budget: Budget for the current run.
    - previous_built_stations: Dictionary of previously built chargers per site.
    - area_demand: Dictionary of demand per area.
    - station_cost: Cost per station.
    - charger_cost: Cost per charger.

    Returns:
    - Dictionary containing results if optimal/suboptimal solution is found.
    - None otherwise.
    """

    model.reset()

    # Update MAX_CHARGERS and apply warm start for 'build' variables
    for var in model.getVars():
        if var.VarName.startswith("build["):
            # Extract site index from variable name
            site = var.VarName.split("[")[1].rstrip("]")
            # If site identifiers are not integers, adjust the extraction accordingly
            # For example, if site names are strings, you might need a different approach
            # Here, we assume site identifiers are integers
            try:
                site = int(site)
            except ValueError:
                # Handle non-integer site identifiers if necessary
                continue

            var.UB = max_chargers  # Update upper bound for chargers at each site
            var.LB = previous_built_stations.get(site, 0)  # Set lower bound to previous built chargers
            var.Start = previous_built_stations.get(site, 0)  # Warm start for 'build' variables

    # Apply warm start for 'is_built' variables
    for var in model.getVars():
        if var.VarName.startswith("is_built["):
            site = var.VarName.split("[")[1].rstrip("]")
            try:
                site = int(site)
            except ValueError:
                continue
            var.Start = 1 if previous_built_stations.get(site, 0) > 0 else 0

    # print("Warm start applied.")

    # Update budget constraint RHS
    budget_constraint = model.getConstrByName("budget_constraint")
    if budget_constraint is None:
        print("Budget constraint not found in the model.")
        return None
    budget_constraint.RHS = budget

    # Ensure updates are applied
    model.update()

    # ---------------------------- RESOLVE THE MODEL ---------------------------------------
    # Turn off Gurobi logging
    model.setParam('OutputFlag', 0)

    # Stop at objective confidence interval of n%
    model.setParam('MIPGap', 0.10)
    # model.setParam('TimeLimit', 200000)  # Stop after 200 seconds

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

        # print("Parameters given:")
        # print(f"BUDGET: {budget}")
        # print(f"STATION_COST: {station_cost}")
        # print(f"CHARGER_COST: {charger_cost}")
        # # print("CAP_SPOT:", cap_spot)
        # print(f"MAX_CHARGERS: {max_chargers}")

        budget_constraint = model.getConstrByName("budget_constraint")
        slack = budget_constraint.Slack
        total_cost_used = budget - slack
        print(f"Total cost used: {total_cost_used}")
        # print(f"Budget constraint slack: {slack}")

        # Calculate total demand coverage
        total_demand_coverage = 0
        total_demand = sum(area_demand.values())  # Total demand across all areas
        for var in model.getVars():
            if var.VarName.startswith("saturation_raw["):
                area_id = var.VarName.split("[")[1].rstrip("]")
                if area_id in area_demand:
                    coverage = min(var.X * area_demand[area_id], area_demand[area_id])
                    total_demand_coverage += coverage

        MILLION = 1000000  # Ensure MILLION is defined within the function
        total_coverage_percentage = (total_demand_coverage / total_demand) * 100 if total_demand > 0 else 0
        print(f"Total Demand Coverage (in Millions): {total_demand_coverage/MILLION:.2f}")
        print(f"Total Demand Coverage Percentage: \033[1;31m{total_coverage_percentage:.2f}%\033[0m")

        # **Added Section: Calculate Number of Stations Built**
        stations_built_1 = sum(
            1 for var in model.getVars()
            if var.VarName.startswith("is_built[") and var.X > 0.5
        )
        # print(f"Total number of stations built 1 is_built: {stations_built_1}")

        stations_built_2 = sum(
            1 for var in model.getVars()
            if var.VarName.startswith("build[") and var.X > 0.5
        )
        # print(f"Total number of stations 2 build: {stations_built_2}")

        chargers_built = sum(
            var.X for var in model.getVars()
            if var.VarName.startswith("build[") and var.X > 0.5
        )
        # print(f"Total number of chargers built: {chargers_built}")

        return {
            "total_demand_coverage": total_demand_coverage,
            "total_coverage_percentage": total_coverage_percentage,
            "objective": model.ObjVal,
            "total_cost_used": total_cost_used,
            "stations_built": stations_built_1  # **Added to the returned dictionary**
        }
    else:
        print("No optimal solution found.")
        return None

def main():
    # Load the model once
    try:
        model = gp.read("./data/model_output/saved_model.mps")
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # Load demand data and warm start data
    try:
        with open("./data/georgia_processed_data/georgia_processed_data.pkl", "rb") as f:
            loaded_data = pickle.load(f)
    except FileNotFoundError:
        print("Data file not found. Please ensure the path is correct.")
        return
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    c = loaded_data['areas_demand']  # Area demand
    tr = loaded_data['trips']
    P = loaded_data['potential_sites']
    A = loaded_data['areas']  # Assuming 'areas' is also needed
    previous_built_stations = {}
    try:
        with open("./data/model_output/built_stations.pkl", "rb") as f:
            previous_built_stations = pickle.load(f)
        # print("Previous built stations loaded.")
    except FileNotFoundError:
        print("No previous solution found. Starting fresh.")
    except Exception as e:
        print(f"Error loading previous built stations: {e}")
        return

    # Define hyperparameter combinations
    MILLION = 1000000
    STATION_COST = 250000  # does not update automatically, only after model.py rerun
    CHARGER_COST = 50000  # does not update automatically, only after model.py rerun

    # Adjustable, update automatically
    budgets = range(10 * MILLION, 111 * MILLION, 10 * MILLION)  # Budgets in dollars
    # Convert budgets to list
    budgets = list(budgets)

    CAP_SPOT = 500000  # CAP_SPOT does not update automatically, only after model.py rerun
    MAX_CHARGERS = 30  # Update MAX_CHARGERS if necessary

    # Placeholder for results
    results = []

    # Solve the model for each budget
    for budget in budgets:
        print(f"\n--- Running for Budget (in millions of $) = {budget / MILLION} ---")

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
                "total_coverage_percentage": result["total_coverage_percentage"],
                "stations_built": result["stations_built"]  # Included here
            })
            print(f"Accumulated Result: Budget={budget / MILLION}M, "
                  f"Total Demand Coverage={result['total_demand_coverage']:.2f}, "
                  f"Percentage={result['total_coverage_percentage']:.2f}%, "
                  f"Stations Built={result['stations_built']}")
        else:
            print(f"Failed to find optimal solution for Budget={budget / MILLION}M.")

    # # Export results to a JSON file
    # output_file = "./data/model_results_totals.json"
    # try:
    #     with open(output_file, "w") as f:
    #         json.dump(results, f, indent=4)
    #     print(f"\nResults saved to {output_file}")
    # except Exception as e:
    #     print(f"Failed to save results: {e}")

    # Uncomment the above lines to enable result exporting

    # print(f"\n RESULTS NOT SAVED")

if __name__ == "__main__":
    main()
