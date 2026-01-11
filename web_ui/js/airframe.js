import * as THREE from 'three';
import { calculateEngineMetrics } from './engine.js';
import { getMotorByThrust } from './motor.js';
import { calculateBatteryMetricsFromWeight } from './battery.js';

export function generateAirframe(
    payloadWeight, payloadLength, payloadWidth, payloadHeight,
    targetWingLoading, thrustToWeightRatio, fuelFraction,
    aspectRatio, taperRatio
) {
    const powerplantType = document.getElementById('powerplant-type')?.value || 'fuel';
    let rootChord, tipChord, semiSpan;
    let sweep = 20;

    // A more sophisticated initial guess for MTOW, accounting for engine/motor weight estimate.
    const estimatedPowerplantWeightFraction = 0.36 * thrustToWeightRatio;
    const airframeFractionGuess = 0.25; // Guess airframe is 25% of MTOW
    const energyFraction = powerplantType === 'electric' ? fuelFraction : fuelFraction; // Battery or fuel fraction
    const denominator = 1 - energyFraction - estimatedPowerplantWeightFraction - airframeFractionGuess;
    let mtow_kg = (payloadWeight + 1.5) / (denominator > 0.1 ? denominator : 0.1); // Avoid division by zero/small numbers
    
    // --- Pre-calculate fixed wing geometry based on initial MTOW estimate ---
    const totalWingPlanformArea = mtow_kg / targetWingLoading;
    const fullSpan = Math.sqrt(totalWingPlanformArea * aspectRatio);
    semiSpan = (fullSpan - payloadWidth) / 2;
    if (semiSpan < 0) semiSpan = 0;

    const rootChordDenominator = (1 + taperRatio) * (fullSpan - payloadWidth) / 2 + payloadWidth;
    rootChord = totalWingPlanformArea / rootChordDenominator;
    tipChord = rootChord * taperRatio;
    // --- End of fixed geometry calculation ---

    let enginePower_kw = 0, engineWeight_kg = 0, engineSize_m = 0, propellerDiameter_m = 0, cruiseSpeed_knots = 0, propellerPitch_in = 0;
    let fuelWeight = 0, airframeWeight = 0, fuselageWeight = 0, wingWeight = 0;
    let motorData = null, batteryData = null;

    for (let i = 0; i < 5; i++) {
        // POWERPLANT MODEL (Fuel Engine or Electric Motor)
        if (powerplantType === 'electric') {
            // Electric motor calculation
            const requiredThrust_N = mtow_kg * 9.81 * thrustToWeightRatio;
            // Fixed-wing disk loading is much lower than multicopters
            // Typical values: 50-150 N/m² for efficient fixed-wing
            // Lower = larger prop = more efficient but slower
            const diskLoading = 100; // N/m^2, optimized for fixed-wing efficiency
            
            // Calculate propeller diameter FIRST (critical for motor selection)
            propellerDiameter_m = Math.sqrt((4 * requiredThrust_N) / (Math.PI * diskLoading));
            
            // Now select motor with correct propeller diameter
            motorData = getMotorByThrust(requiredThrust_N, diskLoading, propellerDiameter_m, 22.2);
            engineWeight_kg = motorData.weight_kg;
            enginePower_kw = motorData.power_W / 1000;
            engineSize_m = motorData.diameter_m;
            cruiseSpeed_knots = 50; // Estimate, similar to fuel
            propellerPitch_in = 0.7 * (propellerDiameter_m / 0.0254);
            
            // Calculate battery weight from fuel fraction (now battery fraction)
            const batteryWeightTarget = mtow_kg * fuelFraction;
            batteryData = calculateBatteryMetricsFromWeight(batteryWeightTarget, 22.2, 50);
            
        } else {
            // Fuel engine calculation (existing)
            ({ enginePower_kw, engineWeight_kg, engineSize_m, propellerDiameter_m, cruiseSpeed_knots, propellerPitch_in } = calculateEngineMetrics(mtow_kg, thrustToWeightRatio));
        }

        // =======================================================================
        // REVISED AND FULLY CORRECTED AIRFRAME WEIGHT CALCULATION
        // =======================================================================

        // --- PHYSICAL CONSTANTS (Calibrated for better realism) ---
        const WING_SKIN_DENSITY = 3.4;      // kg/m^2 (reduced by 25% from 4.5)
        const WING_BENDING_FACTOR = 0.0055;   // Unitless (reduced by 25% from 0.00735)
        const FUSELAGE_SKIN_DENSITY = 6.0;  // kg/m^2 (reduced by 25% from 8.0)
        const FUSELAGE_SHAPE_PENALTY_FACTOR = 1.5;

        // --- Calculation Steps ---

        // 1. FUSELAGE WEIGHT
        const fuselageWettedArea = 2 * (payloadLength * payloadWidth + payloadLength * payloadHeight + payloadWidth * payloadHeight);
        const baseFuselageWeight = fuselageWettedArea * FUSELAGE_SKIN_DENSITY;
        const effectiveDiameter = Math.sqrt((4 / Math.PI) * payloadWidth * payloadHeight);
        const finenessRatio = payloadLength / effectiveDiameter;
        const idealFinenessRatio = 5.0;
        const shapePenalty = 1.0 + FUSELAGE_SHAPE_PENALTY_FACTOR * Math.pow((finenessRatio - idealFinenessRatio) / idealFinenessRatio, 2);
        fuselageWeight = baseFuselageWeight * shapePenalty;

        // 2. WING WEIGHT (uses fixed geometry now)
        const wingSurfaceArea = (rootChord + tipChord) * semiSpan;
        const skinAndRibWeight = wingSurfaceArea * WING_SKIN_DENSITY;

        // Bending Moment Penalty (softened by /2 for longer wings and reduced by 30%)
        const baselineWingLoading = 40; // kg/m^2
        const wingLoadingPenaltyFactor = 0.5;
        const wingLoadingMultiplier = 1 + Math.max(0, (targetWingLoading / baselineWingLoading - 1) * wingLoadingPenaltyFactor);
        const bendingPenalty = (0.7 * WING_BENDING_FACTOR * mtow_kg * Math.pow(fullSpan, 1.5) * (1 + aspectRatio * 0.1) * wingLoadingMultiplier) / 2;
        wingWeight = skinAndRibWeight + bendingPenalty;

        // 3. TOTAL AIRFRAME WEIGHT
        airframeWeight = fuselageWeight + wingWeight;

        // MTOW CALCULATION from components
        const dryWeightWithoutFuel = payloadWeight + engineWeight_kg + airframeWeight;
        mtow_kg = dryWeightWithoutFuel / (1 - fuelFraction);
        fuelWeight = mtow_kg - dryWeightWithoutFuel;
    }

    // --- Center of Mass Calculation ---
    const payloadPosition = new THREE.Vector3(payloadLength / 2, 0, 0);
    const powerplantPosition = new THREE.Vector3(payloadLength + engineSize_m * 1.5 / 2, 0, 0);
    const combinedPayloadCg = payloadPosition.clone().multiplyScalar(payloadWeight + fuelWeight + airframeWeight);
    const powerplantCg = powerplantPosition.clone().multiplyScalar(engineWeight_kg);
    const centerOfMass = new THREE.Vector3()
        .add(combinedPayloadCg)
        .add(powerplantCg)
        .divideScalar(mtow_kg);

    // --- Center of Pressure & Stability Calculation ---
    const taper = tipChord / rootChord;
    const mac = (2 / 3) * rootChord * (1 + taper + taper * taper) / (1 + taper);
    const y_mac = (semiSpan / 3) * (1 + 2 * taper) / (1 + taper);
    const wingArea = (rootChord + tipChord) * semiSpan;
    const payloadArea = payloadLength * payloadWidth;
    const payload_cp_x = payloadLength / 2;
    const target_cp_x = centerOfMass.x + engineSize_m * 1.5;
    const required_wing_ac_x = (target_cp_x * (wingArea + payloadArea) - payload_cp_x * payloadArea) / wingArea;
    const required_x_le_mac = required_wing_ac_x - 0.25 * mac;

    let wingOffset = 0;
    if (y_mac > 0.001) {
        let sweep_rad = Math.atan(required_x_le_mac / y_mac);
        sweep = sweep_rad * 180 / Math.PI;

        if (sweep > 60) {
            sweep = 60;
            const sweep_rad_60 = 60 * Math.PI / 180;
            wingOffset = required_x_le_mac - y_mac * Math.tan(sweep_rad_60);
        } else if (sweep < 0) {
            sweep = 0;
            wingOffset = required_x_le_mac;
        }
    } else {
        sweep = 0;
        wingOffset = required_x_le_mac;
    }

    const final_x_le_sweep = Math.tan(sweep * Math.PI / 180);
    const final_x_mac = y_mac * final_x_le_sweep;
    const final_wing_ac_x = wingOffset + final_x_mac + 0.25 * mac;
    const final_cp_x = (final_wing_ac_x * wingArea + payload_cp_x * payloadArea) / (wingArea + payloadArea);
    let centerOfPressure = new THREE.Vector3(final_cp_x, 0, 0);

    const fuselageVolume = payloadLength * payloadWidth * payloadHeight;
    const wingVolume = wingArea * ((rootChord + tipChord) / 2) * 0.1; // Approximate volume
    const totalVolume = fuselageVolume + wingVolume;

    return {
        geometrics: { 
            semiSpan, rootChord, tipChord, payloadLength, payloadWidth, payloadHeight, 
            engineSize_m, propellerDiameter_m, cruiseSpeed_knots, propellerPitch_in, 
            centerOfMass, centerOfPressure, wingOffset, sweep, enginePower_kw,
            motorDiameter_m: motorData ? motorData.diameter_m : null,
            motorHeight_m: motorData ? motorData.height_m : null,
            motorMaxRpm: motorData ? motorData.max_rpm : null,
            motorKv: motorData ? motorData.kv : null,
            motorThrust_N: motorData ? motorData.thrust_N : null
        },
        weights: { mtow: mtow_kg, payload: payloadWeight, fuel: fuelWeight, powerplant: engineWeight_kg, airframe: airframeWeight },
        volume: totalVolume,
        shape: { rootChord, tipChord, semiSpan, sweep },
        motorData: motorData,
        batteryData: batteryData,
        powerplantType: powerplantType
    };
}
