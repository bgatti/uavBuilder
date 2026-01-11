// sizing.js
// Centralized sizing logic for all drone components.

// --- Constants ---
const PAYLOAD_DENSITY = 800; // kg/m^3 (generic electronics, accounting for internal air)
const BATTERY_DENSITY = 1100; // kg/m^3 (packaged LiPo, lower than raw cell density)

// --- Sizing Functions ---

/**
 * Calculates the dimensions of a battery based on its weight.
 * @param {number} batteryWeight - The weight of the battery in kg.
 * @returns {object} An object with width, height, and depth in meters.
 */
export function getBatteryDimensions(batteryWeight) {
    if (batteryWeight <= 0) return { width: 0, height: 0, depth: 0 };
    const volume = batteryWeight / BATTERY_DENSITY; // m^3
    // Assume a common battery shape (e.g., 4:3:2 ratio) to avoid overly flat packs
    // V = w*h*d = (2d)*(1.5d)*d = 3d^3 => d = cbrt(V/3)
    const depth = Math.cbrt(volume / 3);
    const width = 2 * depth;
    const height = 1.5 * depth;
    return { width, height, depth };
}

/**
 * Calculates the dimensions of a payload based on its weight.
 * @param {number} payloadWeight - The weight of the payload in kg.
 * @returns {object} An object with width, height, and depth in meters.
 */
export function getPayloadDimensions(payloadWeight) {
    if (payloadWeight <= 0) return { width: 0, height: 0, depth: 0 };
    const volume = payloadWeight / PAYLOAD_DENSITY; // m^3
    // Assume a cubic shape for the payload
    const size = Math.cbrt(volume);
    return { width: size, height: size, depth: size };
}

/**
 * Calculates the diameter of the central body.
 * @param {object} batteryDimensions - The dimensions of the battery.
 * @param {object} payloadDimensions - The dimensions of the payload.
 * @returns {number} The diameter of the central body in meters.
 */
export function getCentralBodyDiameter(batteryDimensions, payloadDimensions) {
    // The body needs to be large enough to house the widest component.
    const maxDim = Math.max(
        batteryDimensions.width, batteryDimensions.depth,
        payloadDimensions.width, payloadDimensions.depth
    );
    // Add a margin for the airframe structure itself
    const margin = 0.05; // 5cm
    return maxDim + margin;
}
