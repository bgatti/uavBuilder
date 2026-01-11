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
 * Estimates drone motor characteristics using disk loading and speed of sound constraints.
 *
 * Algorithm:
 * 1. Calculate max RPM based on prop diameter and tip speed limit (80% of speed of sound)
 * 2. Determine required KV from max RPM and voltage
 * 3. Select closest available KV from real motor database
 * 4. Return motor specs from real database or estimated specs
 *
 * @param {number} thrust_N The required peak thrust from a single motor in Newtons.
 * @param {number} disk_loading_N_m2 The disk loading of the propeller system in Newtons per square meter.
 * @param {number} [prop_diameter_m=0.3] The propeller diameter in meters.
 * @param {number} [voltage_V=22.2] The nominal battery voltage (e.g., 22.2 for 6S, 14.8 for 4S). Defaults to 6S.
 * @returns {object} An object containing the estimated motor properties.
 */
export function getMotorByThrust(thrust_N, disk_loading_N_m2, prop_diameter_m = 0.3, voltage_V = 22.2) {
    // --- Speed of Sound Constraint ---
    const SPEED_OF_SOUND = 343; // m/s at sea level
    const TIP_SPEED_LIMIT = 0.8 * SPEED_OF_SOUND; // 80% of speed of sound (typical for efficiency)
    
    // Calculate max RPM based on prop diameter and tip speed limit
    // Tip Speed = (RPM / 60) * π * Diameter
    // RPM = (Tip Speed * 60) / (π * Diameter)
    const max_rpm = (TIP_SPEED_LIMIT * 60) / (Math.PI * prop_diameter_m);
    
    // Calculate required KV from max RPM and voltage
    // KV = RPM / Voltage
    const required_kv = max_rpm / voltage_V;
    
    // Find closest available KV from REAL_MOTORS database
    let closest_kv = 100;
    let closest_distance = Math.abs(100 - required_kv);
    
    const available_kvs = [...new Set(REAL_MOTORS.map(m => m.KV))].sort((a, b) => a - b);
    for (const kv of available_kvs) {
        const distance = Math.abs(kv - required_kv);
        if (distance < closest_distance) {
            closest_distance = distance;
            closest_kv = kv;
        }
    }
    
    // Find a motor from REAL_MOTORS with this KV that meets thrust requirement
    let selected_motor = null;
    for (const motor of REAL_MOTORS) {
        if (motor.KV === closest_kv && motor.thrust_N >= thrust_N * 0.9) {
            if (!selected_motor || motor.thrust_N < selected_motor.thrust_N) {
                selected_motor = motor;
            }
        }
    }
    
    // If no exact match, estimate specs using power-thrust relationship
    if (!selected_motor) {
        // Estimate power from thrust using empirical relationship: Power ≈ Thrust ^ 1.1
        const estimated_power_W = Math.pow(thrust_N, 1.1) * 50;
        
        // Find closest motor by power as fallback
        let best_motor = REAL_MOTORS[0];
        let best_diff = Math.abs(best_motor.Max_Power_W - estimated_power_W);
        for (const motor of REAL_MOTORS) {
            const diff = Math.abs(motor.Max_Power_W - estimated_power_W);
            if (diff < best_diff) {
                best_diff = diff;
                best_motor = motor;
            }
        }
        selected_motor = best_motor;
    }
    
    // Normalize and return the selected motor
    return normalizeMotor(selected_motor);
}
