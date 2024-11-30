import pandas as pd
import random


def GENERATE_DATA(
    N_AREAS,
    N_POTENTIAL_SITES,
    CHARGERS_BUDGET_LIMIT,
    CAP_SPOT,
    MAX_CHARGERS,
    SEED=None
):
    """
    Generates the trips matrix and area capacities for EV charging station placement.

    Parameters:
    - N_AREAS (int): Total number of areas.
    - N_POTENTIAL_SITES (int): Number of potential charging station sites.
    - CHARGERS_BUDGET_LIMIT (int): Maximum number of chargers that can be built.
    - CAP_SPOT (int): Number of trips each charging spot can serve.
    - MAX_CHARGERS (int): Maximum number of chargers per site.
    - SEED (int, optional): Seed for random number generators to ensure reproducibility.

    Returns:
    - tr_matrix (pd.DataFrame): Trips matrix with potential sites as rows and areas as columns.
    - c_df (pd.DataFrame): DataFrame containing capacities for each area.
    """

    # Set the random seed for reproducibility
    if SEED is not None:
        random.seed(SEED)

    # Define areas
    A = [f"Area{i}" for i in range(1, N_AREAS + 1)]

    # Randomly select potential sites from areas
    P = random.sample(A, N_POTENTIAL_SITES)

    # Define hubs and residential areas
    # Assume first half of A are hubs and second half are residential areas
    half = N_AREAS // 2
    hubs = A[:half]
    residential_areas = A[half:]

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

    # Generate capacities for each area (higher for residential areas)
    c = {}
    for j in A:
        if j in residential_areas:
            c[j] = random.randint(800, 1000)  # Higher population for residential areas
        else:
            c[j] = random.randint(100, 200)   # Lower population for hubs

    # Convert the trips dictionary `tr` to a DataFrame
    tr_matrix = pd.DataFrame(0, index=sorted(P), columns=A)  # Initialize with zeros

    # Populate the DataFrame with trip values
    for (i, j), value in tr.items():
        tr_matrix.loc[i, j] = value

    # Convert capacities dictionary `c` to a DataFrame
    c_df = pd.DataFrame.from_dict(c, orient='index', columns=['Capacity']).T

    # Display trips matrix
    print("\nTrips Matrix (Potential Station Sites as rows, Areas as columns):")
    print(tr_matrix)

    # Display capacities matrix
    print("\nArea Capacities (c):")
    print(c_df)

    # Display constants
    print("\nConstants:")
    print("CHARGERS_BUDGET_LIMIT:", CHARGERS_BUDGET_LIMIT)
    print("CAP_SPOT:", CAP_SPOT)
    print("MAX_CHARGERS:", MAX_CHARGERS)

    return A, P, c, tr 