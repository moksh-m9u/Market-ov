# Market-ov
Attribution modelling via markov chains
Well a random blog on medium inspired me............... so here we are
---

## Data Description

The dataset used in this project is in CSV format, comprising 586,737 rows and 6 columns. The columns include:
- **`Cookie`**: Anonymized customer ID.
- **`Time`**: Date and time of the customer visit.
- **`Interaction`**: Type of interaction (categorical variable).
- **`Conversion`**: Binary indicator (0 for not converted, 1 for converted).
- **`Conversion Value`**: Monetary value of the conversion event.
- **`Channel`**: The marketing channel responsible for directing the customer to the site (target variable).

---

## Approach

1. **Import Dependencies**:
   - Load all required libraries and modules for the analysis.

2. **Data Import**:
   - Read the dataset into a Pandas DataFrame.

3. **Exploratory Data Analysis (EDA)**:
   - Generate a comprehensive EDA report using `Pandas-Profiling`.
   - Perform data cleaning and visualization to understand key trends and patterns.

4. **Build Single Touch Attribution Models**:
   - **Last Touch Attribution Model**: Assign credit to the last channel before conversion.
   - **First Touch Attribution Model**: Assign credit to the first channel in the customer journey.
   - **Last Non-Direct Touch Attribution Model**: Assign credit to the last channel before conversion, excluding direct visits.

5. **Build Multi-Touch Attribution Models**:
   - **Linear Attribution Model**: Distribute credit evenly across all touchpoints.
   - **Position-Based (U-Shaped) Attribution Model**: Assign 40% credit to the first and last touchpoints, and 20% to the intermediate points.
   - **Position Decay Attribution Model**: Assign decreasing credit to touchpoints as they get further from the conversion event.

6. **Build Probabilistic Attribution Models**:
   - **Markov Attribution Model**: Use transition probabilities to evaluate channel contributions.
   - **Shapley Value Model**: Apply cooperative game theory to determine the marginal contribution of each channel.

7. **Results**:
   - Consolidate results from all models into tables for comparison.
   - Generate and save visualizations to illustrate model outputs.

8. **Budget Optimization Engine**:
   - Use optimization algorithms (e.g., GEKKO) to allocate marketing budgets efficiently across channels based on model results.

---

Reference Blog - https://medium.com/@akanksha.etc302/attribution-modeling-using-markov-chain-88fc6c0a499e
