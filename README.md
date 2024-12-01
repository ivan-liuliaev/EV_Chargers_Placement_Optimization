# Georgia public EV chargers placement optimization 🔮

![](assets/front_animation.gif)

## Results summary

* The model demonstrates a **7% improvement** over the baseline heuristic algorithm
* This translates to over **$4 000 000 in savings** on the initiative's implementation budget
* After analyzing Budget-Performance sensitivity, **$60 000 000 is revealed as the optimal budget** that maximizes overall profit



## Contents
- [Insights](#insights)
- [Problem statement](#problem-statement)
- [Solution design](#solution-design)
- [Results](#model-results)



## Problem statement
### Come up with optimal locations for EV charging stations within the state of Georgia 🚗 🔌 


### Inputs
- population density
- traffic patterns
- existing infrastructure
- budget constraints
- profitability concerns


### Evaluation criteria
-  Share of Electric Vehicle owners with seamless access to public charging
Seemless means the charger is located at the place he currently travels to on a regular and thus do not have to spend additional time and effort to charge


## Data
- 3.5 million Georgia monthly Origin-Destination trips dataset
- Population data on 2796 US Census Tracts in Georgia
- 7446 Georgia US Census blocks groups shapefiles


## Solution design
### Mixed-Integer Programming (MIP) model

> Mathematical programming is a declarative approach where the modeler formulates a mathematical optimization model that captures the key aspects of a complex decision problem. 

The model is formulated using the GurobiPy modeling syntax and solved with the Gurobi Optimizer.


### Model Formulation:

### Sets and Indices
- **Areas (A):** The different geographical areas that require EV charging coverage.
- **Potential Sites (P):** Locations where EV charging stations can potentially be built.
- **Trips (tr[P,A]):** Pairs representing trips from a potential site P to an area A.

### Parameters
- **Budget (B):** The total available budget for building charging stations and installing chargers.
- **Station Cost:** The fixed cost required to build a charging station at a potential site.
- **Charger Cost:** The cost to install each charger at a charging station.
- **Capacity per Spot (CAP_SPOT):** The maximum number of trips that each charging spot can serve.
- **Maximum Chargers (MAX_CHARGERS):** The upper limit on the number of chargers that can be installed at any potential site.
- **Areas Demand (c):** The demand for EV charging in each area.
- **Trips (tr):** The number of trips from each potential site to each area.

### Decision Variables
- **Build (build[j]):** The number of charging spots to build at each potential site.
- **Served (served[i, j]):** The number of trips from site *i* to area *j* that are served by the charging stations.

### Helper Variables
- **Saturation Level (z[j]):** Represents the level of demand coverage in each area, ranging from 0 to 1.
- **Raw Saturation (saturation_raw[j]):** An intermediate variable used to calculate the saturation level for each area.
- **Is Built (is_built[j]):** A binary variable indicating whether a charging station is built at a potential site.

### Objective Function
- **Maximize Total Effective Coverage:** The goal is to maximize the sum of the saturation levels across all areas, weighted by their respective demands. This ensures that the EV charging infrastructure effectively covers the areas with higher demand.

### Constraints

1. **Capacity Constraint:**
   - The total number of trips served from each potential site cannot exceed the product of the number of charging spots built at that site and the capacity per spot.

2. **Trip Limit Constraint:**
   - The number of trips served from a potential site to an area cannot exceed the actual number of trips between them.

3. **Saturation Calculation:**
   - For each area, the raw saturation is calculated by dividing the total served trips by the area's demand. This raw value is then used to determine the actual saturation level.

4. **Linking Build and Is_Built Variables:**
   - If a charging station is built at a potential site (i.e., the number of chargers is greater than zero), the corresponding binary variable is set to one. Conversely, the number of chargers cannot exceed the maximum allowed if no station is built.

5. **Saturation Level Constraint:**
   - The saturation level for each area is the minimum of the raw saturation and one, ensuring that coverage does not exceed 100%.

6. **Budget Constraint:**
   - The total cost of building charging stations and installing chargers must not exceed the available budget. This includes both the fixed costs for stations and the variable costs for chargers.




## Model Results
### Chargers Placement
![](assets/placement.png)

### Resulting Coverage
![](assets/coverage.png)

### Top areas served by each Charging Station
![](assets/trips.png)

### Optimal Budget: Budget-Performance sensitivity
![](assets/curves.png)
