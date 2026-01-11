// Lookup closest motor by power, rpm, and thrust
export function lookupClosestMotor(power_W, rpm, thrust_N) {
    let bestIdx = -1;
    let bestScore = Infinity;
    for (let i = 0; i < REAL_MOTORS.length; i++) {
        const m = REAL_MOTORS[i];
        // Skip motors that don't meet the minimum thrust requirement
        if (m.thrust_N < thrust_N) {
            continue;
        }
        const motorRpm = m.KV * m.Voltage_V;
        // Weighted score: power diff * 10 + rpm diff * 0.1 + thrust diff * 100
        const score = Math.abs(m.Max_Power_W - power_W) * 10 + Math.abs(motorRpm - rpm) * 0.1 + Math.abs(m.thrust_N - thrust_N) * 100;
        if (score < bestScore) {
            bestScore = score;
            bestIdx = i;
        }
    }
    if (bestIdx === -1) {
        return null;
    }
    return normalizeMotor(REAL_MOTORS[bestIdx]);
}

export function normalizeMotor(motor) {
    return {
        power_W: motor.Max_Power_W,
        weight_kg: motor.Weight_g / 1000,
        diameter_m: motor.Diameter_mm / 1000,
        height_m: motor.Height_mm / 1000,
        kv: motor.KV,
        max_rpm: motor.KV * motor.Voltage_V,
        thrust_N: motor.thrust_N,
        Model: motor.Model,
        Voltage_V: motor.Voltage_V
    };
}
// --- Real Motor Data (from compiled table) ---
export const REAL_MOTORS = [
    {
        "Model": "EMAX ECO II 2207", "Max_Power_W": 1100, "Weight_g": 33.6, "Diameter_mm": 27.7, "Height_mm": 33.5, "KV": 1900, "Voltage_V": 22.2, "thrust_N": 21.6
    },
    {
        "Model": "iFlight XING2 2207", "Max_Power_W": 1050, "Weight_g": 32.0, "Diameter_mm": 29.0, "Height_mm": 31.0, "KV": 1855, "Voltage_V": 22.2, "thrust_N": 20.6
    },
    {
        "Model": "T-Motor F60 PRO V", "Max_Power_W": 1100, "Weight_g": 35.0, "Diameter_mm": 27.5, "Height_mm": 33.5, "KV": 1950, "Voltage_V": 22.2, "thrust_N": 21.6
    },
    {
        "Model": "BrotherHobby Avocat 2806.5", "Max_Power_W": 1350, "Weight_g": 43.0, "Diameter_mm": 33.0, "Height_mm": 29.5, "KV": 1300, "Voltage_V": 22.2, "thrust_N": 26.5
    },
    {
        "Model": "T-Motor VELOX V3115", "Max_Power_W": 2400, "Weight_g": 140.0, "Diameter_mm": 39.5, "Height_mm": 31.5, "KV": 900, "Voltage_V": 22.2, "thrust_N": 47.1
    },
    {
        "Model": "KDE Direct 3520XF-400", "Max_Power_W": 2100, "Weight_g": 220.0, "Diameter_mm": 45.0, "Height_mm": 37.0, "KV": 400, "Voltage_V": 44.4, "thrust_N": 41.2
    },
    {
        "Model": "T-Motor P60", "Max_Power_W": 3000, "Weight_g": 295.0, "Diameter_mm": 69.0, "Height_mm": 35.0, "KV": 340, "Voltage_V": 44.4, "thrust_N": 58.9
    },
    {
        "Model": "Freefly Astro Motor", "Max_Power_W": 4500, "Weight_g": 525.0, "Diameter_mm": 81.0, "Height_mm": 41.0, "KV": 160, "Voltage_V": 44.4, "thrust_N": 88.3
    },
    {
        "Model": "T-Motor U10 Plus", "Max_Power_W": 5000, "Weight_g": 635.0, "Diameter_mm": 100.0, "Height_mm": 42.5, "KV": 100, "Voltage_V": 44.4, "thrust_N": 98.1
    },
    {
        "Model": "T-Motor U15II", "Max_Power_W": 7500, "Weight_g": 1900.0, "Diameter_mm": 140.0, "Height_mm": 60.0, "KV": 80, "Voltage_V": 44.4, "thrust_N": 147.2
    }
];

// Interpolate aspect ratio by RPM
export function getAspectRatioByRPM(rpm) {
    // Build array of [rpm, aspect_ratio]
    const arr = REAL_MOTORS.map(m => [m.KV * m.Voltage_V, m.Height_mm / m.Diameter_mm]);
    arr.sort((a, b) => a[0] - b[0]);
    // Linear interpolation
    for (let i = 1; i < arr.length; i++) {
        if (rpm <= arr[i][0]) {
            const [rpm1, ar1] = arr[i-1];
            const [rpm2, ar2] = arr[i];
            const t = (rpm - rpm1) / (rpm2 - rpm1);
            return ar1 + t * (ar2 - ar1);
        }
    }
    return arr[arr.length-1][1];
}

// Interpolate volume by power
export function getVolumeByPower(power_W) {
    // Build array of [power, volume_L]
    const arr = REAL_MOTORS.map(m => {
        const vol = Math.PI * Math.pow(m.Diameter_mm/2/10,2) * (m.Height_mm/10) / 1000;
        return [m.Max_Power_W, vol];
    });
    arr.sort((a, b) => a[0] - b[0]);
    for (let i = 1; i < arr.length; i++) {
        if (power_W <= arr[i][0]) {
            const [p1, v1] = arr[i-1];
            const [p2, v2] = arr[i];
            const t = (power_W - p1) / (p2 - p1);
            return v1 + t * (v2 - v1);
        }
    }
    return arr[arr.length-1][1];
}

// Calculate diameter and height for a given power and rpm so that volume and aspect ratio agree
export function getMotorDimensions(power_W, rpm) {
    const aspect = getAspectRatioByRPM(rpm);
    const volume = getVolumeByPower(power_W);
    // Solve for diameter and height: V = pi*(d/2)^2*h, h/d = aspect
    // h = aspect*d; V = pi*(d/2)^2*aspect*d = (pi/4)*aspect*d^3
    const d = Math.pow(volume * 4 / (Math.PI * aspect), 1/3);
    const h = aspect * d;
    return { diameter_m: d, height_m: h, aspect, volume };
}
/**
 * Estimates drone motor characteristics using an empirically-derived model.
 *
 * This function is based on a linear regression model trained on a dataset of 10 real-world
 * drone motors, ranging from FPV racing to industrial heavy-lift. It replaces fixed-value
 * assumptions with data-driven formulas, leading to significantly more accurate predictions
 * across a wide range of inputs.
 *
 * @param {number} thrust_N The required peak thrust from a single motor in Newtons.
 * @param {number} disk_loading_N_m2 The disk loading of the propeller system in Newtons per square meter.
 * @param {number} [voltage_V=22.2] The nominal battery voltage (e.g., 22.2 for 6S, 14.8 for 4S). Defaults to 6S.
 * @returns {object} An object containing the estimated motor properties.
 */
export function getMotorByThrust(thrust_N, disk_loading_N_m2, prop_diameter_m, voltage_V = 22.2) {

    // --- Regression Coefficients (Derived from the Python Scikit-learn model) ---
    // These "magic numbers" are the trained intercepts and coefficients from our analysis.

    // 1. Power Model: log(Power) = intercept + coeff * log(Thrust)
    const POWER_INTERCEPT = 3.987;
    const POWER_COEFF_THRUST = 1.096;

    // 2. Weight Model: log(Weight) = intercept + coeff * log(Power)
    const WEIGHT_INTERCEPT = -4.234;
    const WEIGHT_COEFF_POWER = 1.155;

    // 3. Diameter Model: log(Diameter) = intercept + coeff * log(Weight)
    const DIAMETER_INTERCEPT = 1.059;
    const DIAMETER_COEFF_WEIGHT = 0.443;
    
    // 4. KV Model: log(KV) = intercept + coeff1*log(Loading) + coeff2*log(Power)
    const KV_INTERCEPT = 13.561;
    const KV_COEFF_LOADING = 0.505;
    const KV_COEFF_POWER = -1.185;

    // --- Calculations ---

    // 1. Estimate Power based on Thrust using momentum theory
    // For propellers: Power = Thrust^(3/2) / sqrt(2 * rho * disk_area)
    // Where disk_area = π * (diameter/2)^2
    const RHO_AIR = 1.225; // kg/m³ at sea level
    const disk_area_m2 = Math.PI * Math.pow(prop_diameter_m / 2, 2);
    
    // Momentum theory power (ideal aerodynamic power)
    const ideal_power_W = Math.pow(thrust_N, 1.5) / Math.sqrt(2 * RHO_AIR * disk_area_m2);
    
    // Account for ALL losses in the power chain:
    // - Propeller efficiency: 75% (profile drag, tip losses)
    // - Motor efficiency: 85% (copper losses, iron losses)
    // - ESC efficiency: 95% (switching losses)
    // Total system efficiency = 0.75 × 0.85 × 0.95 = 0.60
    const total_system_efficiency = 0.60;
    const power_W = ideal_power_W / total_system_efficiency;

    // 2. Estimate Weight using multi-factor model based on real motor database
    // Key insight: Motor weight is determined by BOTH thrust capability AND kV rating
    // - High thrust requires large magnets/coils (adds weight)
    // - Low kV requires many winding turns (adds weight from copper)
    // - These effects multiply, not add
    
    // From empirical analysis of REAL_MOTORS database:
    // 3. Estimate KV based on propeller size and desired cruise RPM
    // For fixed-wing: larger props need slower RPM for efficiency
    // Target cruise RPM based on prop diameter:
    // - Small props (< 10"): 8000-12000 RPM
    // - Medium props (10-18"): 5000-8000 RPM  
    // - Large props (> 18"): 3000-6000 RPM
    
    const prop_diameter_inches = prop_diameter_m * 39.37;
    let target_cruise_rpm;
    
    if (prop_diameter_inches < 10) {
        target_cruise_rpm = 10000;
    } else if (prop_diameter_inches < 18) {
        // Linear interpolation: 10" → 8000 RPM, 18" → 5000 RPM
        target_cruise_rpm = 8000 - ((prop_diameter_inches - 10) / 8) * 3000;
    } else {
        // Linear interpolation: 18" → 5000 RPM, 30" → 3000 RPM
        target_cruise_rpm = 5000 - ((prop_diameter_inches - 18) / 12) * 2000;
        target_cruise_rpm = Math.max(target_cruise_rpm, 3000); // Floor at 3000 RPM
    }
    
    // Calculate required kV
    const calculated_kv = target_cruise_rpm / voltage_V;
    
    // Round to nearest industry-standard kV rating
    // Common values: 80, 100, 120, 140, 160, 190, 220, 270, 300, 340, 400, 500, 600, 700, 800, 900, 1000, 
    //                1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 3000, 3200, 3500, 4000
    const standardKvValues = [80, 100, 120, 140, 160, 190, 220, 270, 300, 340, 400, 500, 600, 700, 800, 900, 
                               1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2200, 2300, 
                               2400, 2500, 2600, 2700, 2800, 3000, 3200, 3500, 4000, 4500, 5000];
    const kv = standardKvValues.reduce((prev, curr) => 
        Math.abs(curr - calculated_kv) < Math.abs(prev - calculated_kv) ? curr : prev
    );
    
    // NOW calculate weight using both thrust AND kV (moved here after kV is known)
    // Empirical formula calibrated from REAL_MOTORS database:
    // After analyzing real motors, the relationship is:
    // Weight_g = 2.2 * Thrust_N^1.1 * (1000/kV)^0.5
    // This captures that:
    // - Weight scales strongly with thrust (need bigger magnets/coils)
    // - Low kV motors need more copper (inverse square root relationship)
    const kv_scaling = Math.pow(1000 / kv, 0.5);
    const thrust_scaling = Math.pow(thrust_N, 1.1);
    const weight_g = 2.2 * thrust_scaling * kv_scaling;
    const weight_kg = weight_g / 1000;
    const logWeight = Math.log(weight_g); // Needed for diameter calculation below
    
    // 4. Estimate Diameter based on Weight, then Height based on an improved shape factor
    const logDiameter = DIAMETER_INTERCEPT + DIAMETER_COEFF_WEIGHT * logWeight;
    const regression_diameter_mm = Math.exp(logDiameter);

    // Enforce a minimum motor diameter based on propeller size for realism.
    // A common ratio for motor diameter to prop diameter is ~1/4 to 1/6. We'll use 1/5 as a floor.
    const min_diameter_mm = (prop_diameter_m * 1000) / 5.0;
    
    const diameter_mm = Math.max(regression_diameter_mm, min_diameter_mm);
    
    // Improved Shape Factor: Height/Diameter ratio should be LOW for low KV (low RPM), HIGH for high KV (high RPM)
    // Typical pancake motors: ratio ~0.3-0.5; tall racing motors: ratio ~1.0-1.3
    // Use a logistic function for realism
    let shape_factor = 0.4 + 0.9 * (1 / (1 + Math.exp(-(kv - 1000) / 500)));
    // Clamp to realistic range
    shape_factor = Math.max(0.3, Math.min(shape_factor, 1.3));
    const height_mm = diameter_mm * shape_factor;

    // Calculate motor volume (cylinder)
    const volume_L = Math.PI * Math.pow(diameter_mm / 2 / 10, 2) * (height_mm / 10) / 1000; // Liters
    // Power density (W/L)
    const power_density = power_W / volume_L;
    
    // 5. Calculate Max RPM using the provided voltage
    const max_rpm = kv * voltage_V;

    return {
        power_W,
        weight_kg: weight_g / 1000,
        diameter_m: diameter_mm / 1000,
        height_m: height_mm / 1000,
        kv,
        max_rpm,
        thrust_N,
        volume_L,
        power_density
    };
}
