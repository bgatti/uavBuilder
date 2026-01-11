import { generateAirframe } from './airframe.js';

// Helper function to format kg values with decimals for values < 100
function formatKg(value) {
    if (value < 100) {
        return value.toFixed(1);
    }
    return value.toFixed(0);
}

export function calculateMetrics(changedSliderId) {
    const payloadWeight = parseFloat(document.getElementById('payload-weight').value);
    const payloadLength = parseFloat(document.getElementById('payload-length').value);
    const payloadWidth = parseFloat(document.getElementById('payload-width').value);
    const payloadHeight = parseFloat(document.getElementById('payload-height').value);
    const targetWingLoading = parseFloat(document.getElementById('target-wing-loading').value);
    const thrustToWeightRatio = parseFloat(document.getElementById('thrust-weight-ratio').value);
    const fuelFraction = parseFloat(document.getElementById('fuel-fraction').value) / 100.0;

    const aspectRatio = parseFloat(document.getElementById('aspect-ratio').value);
    const taperRatio = parseFloat(document.getElementById('taper-ratio').value);

    const result = generateAirframe(
        payloadWeight, payloadLength, payloadWidth, payloadHeight,
        targetWingLoading, thrustToWeightRatio, fuelFraction,
        aspectRatio, taperRatio
    );
    
    const { geometrics, weights, volume, shape, motorData, batteryData, powerplantType } = result;

    // Update electric motor and battery displays
    if (powerplantType === 'electric' && motorData && batteryData) {
        updateElectricDisplays(motorData, batteryData, weights.mtow, geometrics.enginePower_kw);
    }

    // --- Update UI Sliders and Labels ---
    document.getElementById('tw-label').textContent = thrustToWeightRatio.toFixed(2);
    document.getElementById('target-wl-label').textContent = targetWingLoading.toFixed(0);
    document.getElementById('fuel-frac-label').textContent = (fuelFraction * 100).toFixed(0);
    document.getElementById('pw-kg-label').textContent = payloadWeight;
    document.getElementById('aspect-ratio-label').textContent = aspectRatio.toFixed(1);
    document.getElementById('taper-ratio-label').textContent = taperRatio.toFixed(2);
    const propPitch = parseFloat(document.getElementById('prop-pitch-slider').value);
    document.getElementById('prop-pitch-label').textContent = propPitch.toFixed(2);
    document.getElementById('pl-dims-label').textContent = `${payloadLength} / ${payloadWidth} / ${payloadHeight}`;
    
    document.getElementById('mtow-display').textContent = `${formatKg(weights.mtow)} kg`;
    const finalWingArea = (geometrics.rootChord + geometrics.tipChord) * geometrics.semiSpan + payloadLength * payloadWidth;
    document.getElementById('current-wl-display').textContent = `${(weights.mtow / finalWingArea).toFixed(1)} kg/m²`;

    return { geometrics, weights };
}

function updateElectricDisplays(motorData, batteryData, mtow, powerKw) {
    // Update motor displays
    const motorModelDisplay = document.getElementById('motor-model-display');
    const motorPowerDisplay = document.getElementById('motor-power-display');
    const motorWeightDisplay = document.getElementById('motor-weight-display');
    const motorKvDisplay = document.getElementById('motor-kv-display');
    const motorRpmDisplay = document.getElementById('motor-rpm-display');
    const motorThrustDisplay = document.getElementById('motor-thrust-display');
    
    if (motorModelDisplay) motorModelDisplay.textContent = 'Calculated Motor';
    if (motorPowerDisplay) motorPowerDisplay.textContent = `${(motorData.power_W).toFixed(0)} W (${(motorData.power_W/1000).toFixed(2)} kW)`;
    if (motorWeightDisplay) motorWeightDisplay.textContent = `${(motorData.weight_kg * 1000).toFixed(1)} g (${formatKg(motorData.weight_kg)} kg)`;
    if (motorKvDisplay) motorKvDisplay.textContent = `${motorData.kv.toFixed(0)} kV`;
    if (motorRpmDisplay) motorRpmDisplay.textContent = `${motorData.max_rpm.toFixed(0)} RPM`;
    if (motorThrustDisplay) motorThrustDisplay.textContent = `${motorData.thrust_N.toFixed(1)} N (${formatKg(motorData.thrust_N / 9.81)} kg)`;
    
    // Update battery displays
    const batteryModelDisplay = document.getElementById('battery-model-display');
    const batteryWeightDisplay = document.getElementById('battery-weight-display');
    const batteryCRatingDisplay = document.getElementById('battery-c-rating-display');
    const batteryCapacityDisplay = document.getElementById('battery-capacity-spec-display');
    const batteryVoltageDisplay = document.getElementById('battery-voltage-spec-display');
    const batteryEnergyDisplay = document.getElementById('battery-energy-display');
    const enduranceDisplay = document.getElementById('endurance-display');
    
    if (batteryModelDisplay) batteryModelDisplay.textContent = 'Calculated Battery';
    if (batteryWeightDisplay) batteryWeightDisplay.textContent = `${(batteryData.weight * 1000).toFixed(1)} g`;
    if (batteryCRatingDisplay) batteryCRatingDisplay.textContent = `${batteryData.cRating}C`;
    if (batteryCapacityDisplay) batteryCapacityDisplay.textContent = `${(batteryData.capacity * 1000).toFixed(0)} mAh`;
    if (batteryVoltageDisplay) batteryVoltageDisplay.textContent = `${batteryData.voltage.toFixed(1)} V`;
    if (batteryEnergyDisplay) batteryEnergyDisplay.textContent = `${batteryData.energy_Wh.toFixed(1)} Wh`;
    
    // Note: Endurance is calculated in Cruise Performance section using actual cruise power
}
