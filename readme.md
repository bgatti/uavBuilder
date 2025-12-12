# UAV Range Estimation Logic

This document explains the current logic used in `range_estimator.py` to estimate the range of a UAV powered by a gasoline engine.

The estimation process involves the following steps:

1.  **Estimate Thrust from Engine Horsepower (HP):**
    *   The `estimate_thrust_from_hp` function approximates thrust in Newtons based on the engine's HP. It uses a simplified rule of thumb assuming 25 Newtons of thrust per HP.

2.  **Calculate Maximum Takeoff Weight (MTOW):**
    *   MTOW is calculated based on the estimated thrust and an assumed thrust-to-weight ratio of 0.2. The formula used is: MTOW (kg) = Thrust (N) / 0.2.

3.  **Calculate Maximum Fuel Carriage (Useful Load):**
    *   The `approximate_useful_load_from_mtow` function is used to approximate the useful load in kg based on the calculated MTOW. This function uses a 2nd-degree polynomial regression model derived from data (Model 2).
    *   It is assumed that 100% of this useful load is fuel.

4.  **Calculate Cruising Speed:**
    *   Cruising speed in km/h is estimated based on MTOW and 75% of the engine's HP. A simplified power loading approach is used, with a scaling factor (`power_loading_to_speed_factor`) derived from a reference aircraft (Cessna 172) to convert the power loading to speed.

5.  **Calculate Estimated Range:**
    *   The `approximate_range_from_speed` function is used to approximate the maximum range in nautical miles based on the estimated cruise speed (converted to knots). This function uses a 2nd-degree polynomial regression model derived from data (Model 3).
    *   The estimated range in nautical miles is then converted to kilometers.
    *   A check is included to ensure the estimated range is not negative; if it is, the range is set to 0.

This logic provides a simplified estimation of UAV range based on readily available engine data and empirical models for useful load and range based on speed. It's important to note that these are approximations and real-world performance may vary due to various factors not included in this model.
