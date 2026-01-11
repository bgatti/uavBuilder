/**
 * Calculates high-fidelity engine and propeller metrics using a robust, calibrated model.
 * The weight is calculated using a simple, direct linear relationship (Weight(kg) ≈ 1.05 * HP)
 * which is calibrated to real-world engine data in the 40-50 HP class.
 *
 * @param {number} mtow_kg - The current estimated Maximum Takeoff Weight of the aircraft in kg.
 * @param {number} thrustToWeightRatio - The desired thrust-to-weight ratio (unitless).
 * @returns {object} An object containing the calculated engine and propeller specifications.
 */
export function calculateEngineMetrics(mtow_kg, thrustToWeightRatio) {

    // --- Constants for Unit Conversion and Physics ---
    const KG_TO_LBS = 2.20462;
    const HP_TO_KW = 0.7457;
    const KNOTS_TO_FPS = 1.68781;
    const INCHES_TO_METERS = 0.0254;
    const CESSNA_172_TW_RATIO = 0.163;

    // --- Core Model Coefficients ---
    // Thrust Model: A robust power-law fit y = a * x^b
    const thrust_coeffs = { a: 6.2197, b: 0.7550 }; // For Thrust(lbs) = a * HP^b
    
    // Weight Model: A simple, direct linear relationship based on user-provided data and heuristic.
    // This is far more stable and realistic for this engine class.
    const WEIGHT_KG_PER_HP = 1.05;

    // Interpolation is still used for non-critical performance parameters
    const anchorHp = [1, 5, 10, 20, 45, 100];
    const anchorPropRpm = [8000, 7000, 6500, 6000, 5500, 5000];
    const anchorCruiseKnots = [40, 55, 70, 85, 100, 120];

    function interpolate(x, x_values, y_values) {
        if (x <= x_values[0]) return y_values[0];
        if (x >= x_values[x_values.length - 1]) return y_values[y_values.length - 1];
        for (let i = 0; i < x_values.length - 1; i++) {
            if (x >= x_values[i] && x <= x_values[i+1]) {
                const fraction = (x - x_values[i]) / (x_values[i+1] - x_values[i]);
                return y_values[i] + fraction * (y_values[i+1] - y_values[i]);
            }
        }
        return y_values[0];
    }

    // --- Main Calculation Logic ---

    // 1. Determine required thrust in lbs.
    const requiredThrust_lbs = (mtow_kg * KG_TO_LBS) * thrustToWeightRatio;

    // 2. Find required HP by inverting the thrust power-law: HP = (Thrust / a)^(1/b)
    // This correctly finds the horsepower needed to produce the desired thrust.
    const required_hp = Math.pow(requiredThrust_lbs / thrust_coeffs.a, 1 / thrust_coeffs.b);

    // 3. Calculate Engine Weight using the NEW, SIMPLE, and CORRECT linear model.
    const engineWeight_kg = required_hp * WEIGHT_KG_PER_HP;
    const enginePower_kw = required_hp * HP_TO_KW;

    // 4. Calculate Cruise Speed with T/W Modifier
    const baseCruiseSpeed_knots = interpolate(required_hp, anchorHp, anchorCruiseKnots);
    let finalCruiseSpeed_knots = baseCruiseSpeed_knots;
    if (thrustToWeightRatio > CESSNA_172_TW_RATIO) {
        const twDifferencePercent = (thrustToWeightRatio - CESSNA_172_TW_RATIO) / CESSNA_172_TW_RATIO;
        finalCruiseSpeed_knots = baseCruiseSpeed_knots * (1 + twDifferencePercent);
    }

    // 5. Calculate Propeller Dimensions using the FINAL cruise speed.
    const interpolated_rpm = interpolate(required_hp, anchorHp, anchorPropRpm);
    const speed_in_per_s = finalCruiseSpeed_knots * KNOTS_TO_FPS * 12;
    const rpm_per_s = interpolated_rpm / 60;
    const pitch_in = speed_in_per_s / (rpm_per_s * (1 - 0.15));
    const diameter_in = pitch_in / 0.7;

    // 6. Calculate Engine Size (visual approximation)
    const engineSize_m = Math.cbrt(0.0003 * enginePower_kw + 0.001);

    // 7. Return the complete metrics object.
    return {
        enginePower_kw: enginePower_kw,
        engineWeight_kg: engineWeight_kg,
        engineSize_m: engineSize_m,
        propellerDiameter_m: diameter_in * INCHES_TO_METERS,
        propellerPitch_in: pitch_in,
        cruiseSpeed_knots: finalCruiseSpeed_knots
    };
}
