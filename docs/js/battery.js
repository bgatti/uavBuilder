// Example real battery data (expand as needed)
export const REAL_BATTERIES = [
    {
        Model: "Tattu R-Line 1.55Ah", Capacity_Ah: 1.55, Voltage_V: 22.2, C_Rating: 150, Weight_g: 254
    },
    {
        Model: "CNHL Black 1.3Ah", Capacity_Ah: 1.3, Voltage_V: 22.2, C_Rating: 100, Weight_g: 230
    },
    {
        Model: "Tattu Funfly 1.3Ah", Capacity_Ah: 1.3, Voltage_V: 22.2, C_Rating: 100, Weight_g: 218
    },
    {
        Model: "Tattu 5.0Ah", Capacity_Ah: 5.0, Voltage_V: 22.2, C_Rating: 75, Weight_g: 732
    },
    {
        Model: "DJI TB30 4.28Ah", Capacity_Ah: 4.28, Voltage_V: 26.1, C_Rating: 20, Weight_g: 685
    },
    {
        Model: "DJI TB65 5.88Ah", Capacity_Ah: 5.88, Voltage_V: 44.76, C_Rating: 15, Weight_g: 1350
    },
    {
        Model: "Tattu Plus 16Ah", Capacity_Ah: 16.0, Voltage_V: 44.4, C_Rating: 25, Weight_g: 4900
    },
    {
        Model: "Tattu Plus 22Ah", Capacity_Ah: 22.0, Voltage_V: 44.4, C_Rating: 25, Weight_g: 5800
    }
];

// Lookup closest battery by minimum mAh and minimum power (W)
export function lookupClosestBattery(required_mAh, required_power_W) {
        let best = null;
        let reasons = [];
        for (const b of REAL_BATTERIES) {
            const battery_mAh = b.Capacity_Ah * 1000;
            const max_power = b.C_Rating * battery_mAh / 1000 * b.Voltage_V; // C * Ah * V
            if (battery_mAh < required_mAh) {
                reasons.push(`${b.Model}: insufficient mAh (${battery_mAh} < ${required_mAh})`);
                continue;
            }
            if (max_power < required_power_W) {
                reasons.push(`${b.Model}: insufficient power (${max_power.toFixed(1)}W < ${required_power_W}W)`);
                continue;
            }
            if (!best || b.Weight_g < best.Weight_g) {
                best = b;
            }
        }
        if (!best) {
            console.log('No battery found. Reasons:');
            reasons.forEach(r => console.log(r));
        }
        return best;
}
/**
 * Battery prediction model using ML-trained regression weights
 */
// ML-trained regression weights from battery_model_weights.json
const WEIGHT_MODEL = {
    coef: [0.005571665106056689, 2.8917146260985105e-05], // [Energy_Wh, Energy_Wh * C_Rating]
    intercept: -0.05093459703352865
};
const DENSITY_MODEL = {
    coef: [-0.21310792250479096, 12.200035488116326], // [C_Rating, Capacity_Ah]
    intercept: 307.72171161494816
};

/**
 * Comprehensive battery metrics calculation function
 * Consolidates all battery-related calculations in one place
 */
export function calculateBatteryMetrics(capacity_Ah, voltage_V, c_rating) {
    // Use closest standard C-rating for realism
    const standardCRatings = [10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 150];
    const closestCRating = standardCRatings.reduce((prev, curr) => {
        return (Math.abs(curr - c_rating) < Math.abs(prev - c_rating) ? curr : prev);
    });

    const energy_Wh = capacity_Ah * voltage_V;
    
    // Predict weight using regression
    let predicted_weight_kg = WEIGHT_MODEL.intercept
        + WEIGHT_MODEL.coef[0] * energy_Wh
        + WEIGHT_MODEL.coef[1] * (energy_Wh * closestCRating);
    predicted_weight_kg = Math.max(0.020, predicted_weight_kg); // Clamp at 20g

    // Predict volumetric density (Wh/L)
    let predicted_vol_density = DENSITY_MODEL.intercept
        + DENSITY_MODEL.coef[0] * closestCRating
        + DENSITY_MODEL.coef[1] * capacity_Ah;

    // Estimate volume (L)
    const volume_L = energy_Wh / predicted_vol_density;
    
    const batteryEnergyDensity = volume_L > 0 ? energy_Wh / volume_L : 0;

    return {
        weight: predicted_weight_kg,
        cRating: closestCRating,
        volume_L,
        gravimetric_density: energy_Wh / predicted_weight_kg,
        volumetric_density: predicted_vol_density,
        energy_Wh,
        batteryEnergyDensity,
        voltage: voltage_V,
        capacity: capacity_Ah
    };
}

export function getBatteryWeight(capacity_Ah, voltage_V, c_rating) {
    const metrics = calculateBatteryMetrics(capacity_Ah, voltage_V, c_rating);
    return {
        weight: metrics.weight,
        cRating: metrics.cRating,
        volume_L: metrics.volume_L,
        gravimetric_density: metrics.gravimetric_density,
        volumetric_density: metrics.volumetric_density
    };
}

/**
 * Iteratively finds battery capacity (Ah) that matches a target weight (kg).
 * This is a reverse of the weight prediction model.
 */
export function calculateBatteryMetricsFromWeight(targetWeightKg, voltage_V, initial_c_rating) {
    let capacity_Ah = 5.0; // Start with a reasonable guess
    let last_error = Infinity;

    for (let i = 0; i < 50; i++) { // Max 50 iterations to prevent infinite loops
        const metrics = calculateBatteryMetrics(capacity_Ah, voltage_V, initial_c_rating);
        const currentWeightKg = metrics.weight;
        const error = targetWeightKg - currentWeightKg;

        if (Math.abs(error) < 0.001) { // Close enough (1g)
            return metrics;
        }

        // Simple gradient descent-like adjustment
        // The derivative of weight with respect to capacity is roughly constant,
        // so we can do a proportional adjustment.
        // d(Weight)/d(Capacity) is related to WEIGHT_MODEL.coef[0] * voltage
        const derivative = WEIGHT_MODEL.coef[0] * voltage_V;
        if (Math.abs(derivative) < 1e-6) break; // Avoid division by zero

        capacity_Ah += error / derivative * 0.5; // Adjust capacity with damping

        // Prevent oscillations
        if (Math.abs(error) > Math.abs(last_error)) {
             // Over-shot, reduce step size in next iteration if needed, but for now, just break
        }
        last_error = Math.abs(error);

        if (capacity_Ah < 0) {
            capacity_Ah = 0.01; // Clamp to a small positive value
        }
    }

    // Return the best-effort metrics if convergence isn't perfect
    return calculateBatteryMetrics(capacity_Ah, voltage_V, initial_c_rating);
}
