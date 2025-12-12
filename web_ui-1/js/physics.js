// physics.js

/**
 * Calculates the parasitic drag of the drone.
 * @param {number} airspeed - The airspeed of the drone in m/s.
 * @param {object} airframe - The airframe dimensions and properties.
 * @param {object} battery - The battery dimensions and properties.
 * @param {object} payload - The payload dimensions and properties.
 * @returns {number} The parasitic drag in Newtons.
 */
export function calculateParasiticDrag(airspeed, airframe, battery, payload) {
    const airDensity = 1.225; // kg/m^3
    const dragCoefficient = 0.8; // Typical for a non-streamlined body

    // Calculate the frontal area of the drone
    const bodyArea = Math.PI * Math.pow(airframe.bodyDiameter / 2, 2);
    const batteryArea = battery.width * battery.height;
    const payloadArea = payload.width * payload.height;
    const totalArea = bodyArea + batteryArea + payloadArea;

    // Calculate the parasitic drag
    const drag = 0.5 * airDensity * Math.pow(airspeed, 2) * totalArea * dragCoefficient;

    return drag;
}

/**
 * Calculates the induced drag of the drone.
 * @param {number} airspeed - The airspeed of the drone in m/s.
 * @param {number} mtow - The mass of the drone in kg.
 * @param {number} propDiameter - The diameter of a single propeller in m.
 * @param {number} numMotors - The number of motors.
 * @returns {number} The induced drag in Newtons.
 */
export function calculateInducedDrag(airspeed, mtow, propDiameter, numMotors) {
    const T = mtow * 9.81; // Thrust = Weight for level flight
    const rho = 1.225; // Air density
    const A = Math.PI * Math.pow(propDiameter, 2) / 4 * numMotors; // Total disk area
    const Vi = Math.sqrt(T / (2 * rho * A)); // Induced velocity at hover

    if (airspeed < 0.1) {
        return T; // At hover, induced drag is equal to thrust
    }

    // More advanced model for forward flight
    const Vi_forward = T / (2 * rho * A * Math.sqrt(Math.pow(airspeed, 2) + Math.pow(Vi, 2)));
    const induced_drag = T * (Vi_forward / Math.sqrt(Math.pow(airspeed, 2) + Math.pow(Vi, 2)));
    
    return induced_drag;
}

/**
 * Calculates the dynamic thrust of a propeller at a given airspeed.
 * This model accounts for the reduction in thrust as forward speed increases.
 * @param {number} staticThrust_N - The thrust at zero airspeed (in Newtons).
 * @param {number} propPitch_in - The propeller pitch (in inches).
 * @param {number} motorRpm - The rotational speed of the motor (in RPM).
 * @param {number} airspeed_ms - The current airspeed of the drone (in m/s).
 * @returns {number} The estimated thrust in Newtons at the given airspeed.
 */
export function calculatePropellerThrust(staticThrust_N, propPitch_in, motorRpm, airspeed_ms) {
    if (motorRpm <= 0) {
        return 0;
    }

    // 1. Calculate the theoretical maximum pitch speed of the propeller.
    // This is the speed at which the air is pushed backward by the propeller.
    // V_pitch = RPM * Pitch (converted to meters per second)
    const pitch_m = propPitch_in * 0.0254; // Convert pitch from inches to meters
    const rps = motorRpm / 60; // Convert RPM to revolutions per second
    const pitch_speed_ms = rps * pitch_m;

    // 2. Simple linear degradation model for thrust.
    // Thrust decreases as the drone's airspeed approaches the propeller's pitch speed.
    // When airspeed equals pitch speed, the theoretical thrust becomes zero.
    let thrust = staticThrust_N * (1 - (airspeed_ms / pitch_speed_ms));

    // 3. Clamp the thrust to be non-negative.
    return Math.max(0, thrust);
}
