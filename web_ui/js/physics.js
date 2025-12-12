import { generateAirframe } from './airframe.js';

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

    const { geometrics, weights, volume, shape } = generateAirframe(
        payloadWeight, payloadLength, payloadWidth, payloadHeight,
        targetWingLoading, thrustToWeightRatio, fuelFraction,
        aspectRatio, taperRatio
    );

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
    
    document.getElementById('mtow-display').textContent = `${weights.mtow.toFixed(0)} kg`;
    const finalWingArea = (geometrics.rootChord + geometrics.tipChord) * geometrics.semiSpan + payloadLength * payloadWidth;
    document.getElementById('current-wl-display').textContent = `${(weights.mtow / finalWingArea).toFixed(1)} kg/m²`;

    return { geometrics, weights };
}
