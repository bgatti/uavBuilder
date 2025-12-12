// airframe.js
// Utility for airframe calculations and rendering

// Default airframe color
export const AIRFRAME_COLOR = '#808080'; // Gray

// Calculate airframe weight based on a regression model derived from real drone data.
export function calculateAirframeWeight(mtow) {
    // log(Airframe_Weight) = intercept + coeff * log(MTOW)
    const INTERCEPT = -1.4;
    const COEFF_MTOW = 1.1;

    const logMtow = Math.log(mtow);
    const logAirframeWeight = INTERCEPT + COEFF_MTOW * logMtow;
    const airframeWeight = Math.exp(logAirframeWeight);

    return airframeWeight > 0 ? airframeWeight : 0.05;
}

// Estimate the weight of the central body (plates, fasteners, etc.)
function calculateCentralBodyWeight(diameter, total_thrust) {
    // Weight scales with surface area (d^2) and required strength (thrust)
    const area_factor = Math.PI * Math.pow(diameter / 2, 2);
    // Material density and thickness factor (kg/m^2)
    const structural_factor = 2.5; // Heavier for larger drones
    // Strength factor, assuming higher thrust needs more robust center
    const strength_factor = 1 + (total_thrust / 100); // Increases with thrust
    return area_factor * structural_factor * strength_factor * 0.1; // 10% of the theoretical solid weight
}

// Estimate the weight of the motor arms
function calculateArmWeight(length, diameter, num_motors, num_blades) {
    // Carbon fiber tube density approx 1600 kg/m^3
    const density = 1600;
    const wall_thickness = diameter * 0.1; // 10% wall thickness
    const outer_radius = diameter / 2;
    const inner_radius = outer_radius - wall_thickness;
    const cross_sectional_area = Math.PI * (Math.pow(outer_radius, 2) - Math.pow(inner_radius, 2));
    const volume_per_arm = cross_sectional_area * length;
    const weight_per_arm = volume_per_arm * density;

    // More blades create more vibration and stress, requiring stronger (heavier) arms
    const blade_factor = 1 + (num_blades - 2) * 0.15; // +15% weight per blade over 2

    return weight_per_arm * num_motors * blade_factor;
}


import { getBatteryDimensions, getPayloadDimensions, getCentralBodyDiameter } from './sizing.js';

// Calculate motor arm length based on body diameter and propeller diameter
// Calculate recommended arm diameter for carbon fiber tube
// Based on max thrust per motor (N), arm length (m), and safety factor (default 3)
// Assumptions:
// - Arm is a cantilever beam, loaded at the end (motor thrust)
// - Carbon fiber tube, modulus of elasticity ~70 GPa, yield strength ~600 MPa
// - Tube is circular, hollow, with wall thickness = 10% of diameter
// - Overengineering factor (safety) = 3
// - Only considers bending from thrust, not vibration or crash
// Math:
//   Max bending moment M = thrust * arm_length
//   Required section modulus S = M / (yield_strength / safety_factor)
//   For tube: S = (pi/32) * (D^3 - d^3) / D, d = inner diameter
//   Wall thickness t = 0.1 * D, so d = D - 2t = D - 0.2D = 0.8D
//   S = (pi/32) * (D^3 - (0.8D)^3) / D
//   Solve for D
export function calculateArmDiameter(thrust, armLength, safetyFactor = 3) {
    const yieldStrength = 600e6; // Pa (N/m^2)
    const wallFraction = 0.1; // wall thickness = 10% of diameter
    const M = thrust * armLength; // Nm
    const allowableStress = yieldStrength / safetyFactor;
    // Section modulus S required
    const S = M / allowableStress;
    // S = (pi/32) * (D^3 - (0.8D)^3) / D
    // Expand: (D^3 - (0.8D)^3) = D^3 - 0.512D^3 = 0.488D^3
    // S = (pi/32) * 0.488D^3 / D = (pi/32) * 0.488D^2
    // D^2 = S / ((pi/32) * 0.488)
    const denom = (Math.PI / 32) * 0.488;
    const D = Math.sqrt(S / denom);
    return D; // meters
}
// Returns arm length in meters
export function calculateMotorArmLength(bodyDiameter, propDiameter) {
    // Place motors at edge of body plus half prop diameter plus margin
    const margin = 0.1; // meters
    return (bodyDiameter / 2) + (propDiameter / 2) + margin;
}
// (Retaining the old getAirframeComponents for now, but it should be deprecated)
// numMotors: number, mtow: number (kg)
// Returns array of { name, weight, color }
export function getAirframeComponents(numMotors, mtow) {
    // This function is now a placeholder and should be updated
    // to use the new physics-based weight calculation.
    const estimated_weight = 0.15 * mtow; // Simplified placeholder
    return [
        { name: 'frame_and_arms', weight: estimated_weight, color: AIRFRAME_COLOR }
    ];
}

// Apply airframe color to all components
// components: array of { name, color, ... }
export function applyAirframeColor(components) {
    if (!Array.isArray(components)) return [];
    return components.map(comp => ({ ...comp, color: AIRFRAME_COLOR }));
}

// Real drone dataset for airframe interpolation
export const REAL_DRONES = [
  { Model: "DJI Mini 4 Pro", MTOW_kg: 0.249, Empty_Weight_kg: 0.177, Max_Thrust_kg: 0.6 },
  { Model: "Flywoo FlyLens 85", MTOW_kg: 0.25, Empty_Weight_kg: 0.09, Max_Thrust_kg: 1.6 },
  { Model: "GEPRC CineLog35", MTOW_kg: 0.4, Empty_Weight_kg: 0.24, Max_Thrust_kg: 3.2 },
  { Model: "DJI Air 3", MTOW_kg: 0.72, Empty_Weight_kg: 0.49, Max_Thrust_kg: 1.8 },
  { Model: "Parrot Anafi Ai", MTOW_kg: 1.0, Empty_Weight_kg: 0.58, Max_Thrust_kg: 2.5 },
  { Model: "DJI Mavic 3", MTOW_kg: 1.05, Empty_Weight_kg: 0.61, Max_Thrust_kg: 2.5 },
  { Model: "5-inch FPV Drone", MTOW_kg: 1.5, Empty_Weight_kg: 0.4, Max_Thrust_kg: 9.0 },
  { Model: "iFlight Chimera7 Pro", MTOW_kg: 2.0, Empty_Weight_kg: 0.65, Max_Thrust_kg: 6.0 },
  { Model: "DJI Matrice 30", MTOW_kg: 4.0, Empty_Weight_kg: 2.47, Max_Thrust_kg: 10.0 },
  { Model: "DJI Inspire 3", MTOW_kg: 4.6, Empty_Weight_kg: 3.1, Max_Thrust_kg: 11.5 },
  { Model: "Freefly Astro", MTOW_kg: 6.8, Empty_Weight_kg: 4.3, Max_Thrust_kg: 15.0 },
  { Model: "WingtraOne GEN II", MTOW_kg: 14.0, Empty_Weight_kg: 8.0, Max_Thrust_kg: 21.0 },
  { Model: "Freefly Alta X", MTOW_kg: 34.9, Empty_Weight_kg: 10.3, Max_Thrust_kg: 64.0 },
  { Model: "Harris Carrier H6 Hybrid", MTOW_kg: 38.0, Empty_Weight_kg: 18.1, Max_Thrust_kg: 76.0 },
  { Model: "DJI Agras T40", MTOW_kg: 101.0, Empty_Weight_kg: 38.0, Max_Thrust_kg: 198.0 }
];

// The old regression-based model is removed as it was inaccurate.
// The new `calculateAirframeWeight` function provides a more realistic estimation.
