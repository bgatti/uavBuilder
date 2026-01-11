// --- Functions from user's Python script, translated to JS ---

// Helper function to format kg values with decimals for values < 100
function formatKg(value) {
    if (value < 100) {
        return value.toFixed(1);
    }
    return value.toFixed(0);
}

function degrade_power_for_altitude(hp_sea_level, altitude_ft) {
    /** Degrades engine horsepower based on altitude. Rule of thumb: ~3% loss per 1000 ft. */
    const power_loss_factor = 0.03;
    const loss = (altitude_ft / 1000) * power_loss_factor;
    return hp_sea_level * (1 - loss);
}

function get_air_density_ratio(altitude_ft) {
    /**
     * Standard Atmosphere Model to get density ratio (rho/rho_0).
     * This is a simplified but effective model.
     */
    // Simplified exponential pressure model
    return Math.exp(-altitude_ft / 29000);
}

function calculate_thrust_available(hp_curve, prop_efficiency_curve, air_density_ratio, ias_knots) {
    /**
     * Calculates available thrust from a power curve across a range of airspeeds.
     */
    // For low speeds/static, thrust isn't infinite. It's limited by prop characteristics.
    // We'll use a simple static thrust approximation and blend it with the dynamic formula.
    const N_TO_LBF = 0.224809;
    const LBF_TO_N = 4.44822;

    // Simple static thrust approximation (proportional to HP^(2/3) and density)
    const max_hp = Math.max(...hp_curve);
    const static_thrust_lbf = max_hp * 5 * air_density_ratio;

    // We assume the engine can always make max power at a given throttle.
    const power_at_ias = ias_knots.map((ias, i) => {
        const index = Math.floor((ias / 160) * (hp_curve.length -1));
        return hp_curve[Math.min(Math.max(index, 0), hp_curve.length - 1)];
    });

    // Avoid division by zero at IAS=0
    const thrust_dynamic_lbf = power_at_ias.map((p, i) => {
        const ias = ias_knots[i];
        if (ias <= 0) return 0; // Avoid division by zero
        // 1 HP = 550 ft-lbf/s. 1 knot = 1.68781 ft/s.
        // Thrust (lbf) = (HP * 550) / IAS (ft/s)
        const ias_fps = ias * 1.68781;
        return (p * prop_efficiency_curve[i] * 550) / ias_fps;
    });

    // Create a smooth transition from static to dynamic thrust
    const transition_speed = 30; // knots
    const blend_factor = ias_knots.map(ias => Math.min(Math.max(ias / transition_speed, 0), 1));

    const thrust_lbf = ias_knots.map((ias, i) => {
        const thrust = static_thrust_lbf * (1 - blend_factor[i]) + thrust_dynamic_lbf[i] * blend_factor[i];
        // Thrust also directly reduces with air density
        return thrust * air_density_ratio;
    });

    return thrust_lbf;
}


// Helper function to get ISA conditions at a given altitude
function getIsaConditions(altitude_ft) {
    const altitude_m = altitude_ft * 0.3048;
    let temp_c, pressure_pa;

    if (altitude_m < 11000) { // Troposphere
        temp_c = 15 - 0.0065 * altitude_m;
        pressure_pa = 101325 * Math.pow(1 - 0.0065 * altitude_m / 288.15, 5.255);
    } else { // Stratosphere
        temp_c = -56.5;
        pressure_pa = 22632 * Math.exp(-0.000157 * (altitude_m - 11000));
    }
    const temp_k = temp_c + 273.15;
    const density_kg_m3 = pressure_pa / (287.05 * temp_k);
    return density_kg_m3;
}

// Helper function to get propeller efficiency based on advance ratio
function getPropellerEfficiency(advance_ratio) {
    const peak_J = 0.7;
    const max_eff = 0.82;
    return max_eff * Math.exp(-Math.pow(advance_ratio - peak_J, 2) / (2 * Math.pow(0.2, 2)));
}

// --- High-Fidelity Thrust Model ---
function model_engine_torque(rpm, MAX_POWER_W, PEAK_POWER_RPM) {
    const t = MAX_POWER_W / (PEAK_POWER_RPM * 2 * Math.PI / 60);
    let torque_nm = t * (1 - Math.pow((rpm - PEAK_POWER_RPM) / (PEAK_POWER_RPM * 1.5), 2));
    return (rpm > PEAK_POWER_RPM * 1.5 || torque_nm < 0) ? 0 : torque_nm;
}

function get_prop_coefficients(J, design_j) {
    let cp = 0.05 + 0.05 * Math.pow(design_j, 0.5) - 0.05 * (J / 2.0);
    cp = Math.max(0.01, cp);
    let ct = 0.15 * (1 - Math.pow(J / (design_j * 2.5), 1.5));
    ct = Math.max(0, ct);
    return { ct, cp };
}

function model_prop_load_torque(rpm, tas_mps, propellerDiameter_m, design_j, RHO) {
    const rps = rpm / 60.0;
    if (rps === 0) return Infinity;
    const J = tas_mps / (rps * propellerDiameter_m);
    const { cp } = get_prop_coefficients(J, design_j);
    return (cp * RHO * rps**2 * propellerDiameter_m**5) / (2 * Math.PI);
}


function performPowerplantAnalysis(geometrics, weights, dragProfileData) {
    const { mtow, powerplant: engineWeight_kg, fuel: fuelWeight } = weights;
    const { propellerDiameter_m, enginePower_kw } = geometrics;
    const { speeds_kts, total_drags, thrust_available, operating_rpms, best_glide_speed_kts } = dragProfileData;
    const KTS_TO_MS = 0.514444;
    
    // Get powerplant type
    const powerplantType = document.getElementById('powerplant-type')?.value || 'fuel';

    // Find the high-speed cruise intersection point
    let cruise_idx = -1;
    for (let i = speeds_kts.length - 1; i > 0; i--) {
        if (speeds_kts[i] < best_glide_speed_kts) continue;
        if (thrust_available[i] < total_drags[i] && thrust_available[i-1] > total_drags[i-1]) {
            cruise_idx = i;
            break;
        }
    }

    let cruiseSpeed_kts = 0, cruiseThrust_n = 0, cruiseRpm = 0, power_at_cruise_kw = 0;
    let cruiseFailureReason = '';
    
    // Define cruise as 75% of max motor power
    const cruise_power_limit_kw = enginePower_kw * 0.75;
    const cruise_power_limit_W = cruise_power_limit_kw * 1000;
    
    if (cruise_idx > 0) {
        // Simple interpolation for more accuracy
        const t1 = thrust_available[cruise_idx-1], d1 = total_drags[cruise_idx-1];
        const t2 = thrust_available[cruise_idx], d2 = total_drags[cruise_idx];
        const v1 = speeds_kts[cruise_idx-1], v2 = speeds_kts[cruise_idx];
        const r1 = operating_rpms[cruise_idx-1], r2 = operating_rpms[cruise_idx];
        
        const fraction = (d1 - t1) / ((d1 - t1) - (d2 - t2));
        cruiseSpeed_kts = v1 + fraction * (v2 - v1);
        cruiseThrust_n = d1 + fraction * (d2 - d1);
        cruiseRpm = r1 + fraction * (r2 - r1);
        
        // CORRECT: Power = Thrust × Speed (physics fundamental)
        // At cruise, thrust = drag, and power is the work done moving against drag
        const cruiseSpeed_ms = cruiseSpeed_kts * KTS_TO_MS;
        const propeller_efficiency = 0.75; // Typical for cruise conditions
        const motor_efficiency = 0.85; // Brushless motor efficiency
        const esc_efficiency = 0.95; // ESC efficiency
        const total_efficiency = propeller_efficiency * motor_efficiency * esc_efficiency;
        
        // Aerodynamic power (thrust × speed)
        const aero_power_W = cruiseThrust_n * cruiseSpeed_ms;
        
        // Account for efficiencies to get electrical power input
        const electrical_power_W = aero_power_W / total_efficiency;
        
        // ENFORCE: Cruise power cannot exceed 75% of max motor power
        if (electrical_power_W > cruise_power_limit_W) {
            // Motor cannot sustain this cruise point - need to find lower speed
            // Find the speed where power requirement = 75% max power
            // Power = Drag × Speed, so we need to iterate to find the right speed
            
            let found_cruise = false;
            for (let i = 0; i < speeds_kts.length - 1; i++) {
                if (speeds_kts[i] < best_glide_speed_kts) continue;
                
                const v_ms = speeds_kts[i] * KTS_TO_MS;
                const drag_at_v = total_drags[i];
                const power_needed = drag_at_v * v_ms / total_efficiency;
                
                if (power_needed <= cruise_power_limit_W && thrust_available[i] >= drag_at_v) {
                    cruiseSpeed_kts = speeds_kts[i];
                    cruiseThrust_n = drag_at_v;
                    cruiseRpm = operating_rpms[i];
                    power_at_cruise_kw = power_needed / 1000;
                    found_cruise = true;
                    break;
                }
            }
            
            if (!found_cruise) {
                cruiseFailureReason = 'Cannot achieve sustainable cruise within 75% power limit';
                cruiseSpeed_kts = 0;
                cruiseThrust_n = 0;
                cruiseRpm = 0;
                power_at_cruise_kw = 0;
            }
        } else {
            power_at_cruise_kw = electrical_power_W / 1000;
        }
    } else {
        // Determine why cruise cannot be calculated
        const max_thrust = Math.max(...thrust_available);
        const min_drag = Math.min(...total_drags);
        
        if (max_thrust < min_drag) {
            cruiseFailureReason = 'Insufficient thrust for level flight';
        } else {
            cruiseFailureReason = 'Thrust curve does not intersect drag curve';
        }
    }

    // --- Update UI Displays ---
    const enginePowerHp = enginePower_kw * 1.34102;
    document.getElementById('pp-weight-display').textContent = formatKg(engineWeight_kg) + ' kg';
    document.getElementById('pp-hp-display').textContent = enginePowerHp.toFixed(0);
    
    if (powerplantType === 'electric') {
        // Electric Motor - Calculate endurance and range based on battery
        document.getElementById('pp-cruise-speed-display').textContent = cruiseSpeed_kts > 0 ? `${(cruiseSpeed_kts * 1.852).toFixed(0)} kmh (${cruiseSpeed_kts.toFixed(0)} kts)` : (cruiseFailureReason || 'N/A');
        document.getElementById('cruise-thrust-display').textContent = cruiseThrust_n > 0 ? `${formatKg(cruiseThrust_n / 9.81)} kg (${cruiseThrust_n.toFixed(0)} N)` : (cruiseFailureReason || 'N/A');
        document.getElementById('pp-rpm-display').textContent = cruiseRpm > 0 ? cruiseRpm.toFixed(0) : (cruiseFailureReason || 'N/A');
        
        // Battery-specific calculations
        const batteryEnergy_wh = fuelWeight * 200; // Approximate Wh based on battery weight (200 Wh/kg for LiPo)
        const usableEnergy_wh = batteryEnergy_wh * 0.75; // 75% usable capacity
        
        if (power_at_cruise_kw > 0 && cruiseSpeed_kts > 0) {
            const enduranceHours = usableEnergy_wh / (power_at_cruise_kw * 1000);
            const range_km = (cruiseSpeed_kts * KTS_TO_MS) * enduranceHours * 3.6;
            
            document.getElementById('pp-lph-display').textContent = `${(power_at_cruise_kw * 1000).toFixed(0)} W`;
            document.getElementById('fuel-liters-display').textContent = `${batteryEnergy_wh.toFixed(0)} Wh`;
            document.getElementById('fuel-hours-display').textContent = enduranceHours > 0 && isFinite(enduranceHours) ? `${(enduranceHours * 60).toFixed(1)} min` : (cruiseFailureReason || 'N/A');
            document.getElementById('range-display').textContent = range_km > 0 && isFinite(range_km) ? `${range_km.toFixed(0)} km (${(range_km / 1.852).toFixed(0)} nm)` : (cruiseFailureReason || 'N/A');
        } else {
            document.getElementById('pp-lph-display').textContent = cruiseFailureReason || 'N/A';
            document.getElementById('fuel-liters-display').textContent = `${batteryEnergy_wh.toFixed(0)} Wh`;
            document.getElementById('fuel-hours-display').textContent = cruiseFailureReason || 'N/A';
            document.getElementById('range-display').textContent = cruiseFailureReason || 'N/A';
        }
    } else {
        // Fuel Engine - Original calculations
        document.getElementById('pp-cruise-speed-display').textContent = cruiseSpeed_kts > 0 ? `${(cruiseSpeed_kts * 1.852).toFixed(0)} kmh (${cruiseSpeed_kts.toFixed(0)} kts)` : (cruiseFailureReason || 'N/A');
        document.getElementById('cruise-thrust-display').textContent = cruiseThrust_n > 0 ? `${formatKg(cruiseThrust_n / 9.81)} kg (${cruiseThrust_n.toFixed(0)} N)` : (cruiseFailureReason || 'N/A');
        document.getElementById('pp-rpm-display').textContent = cruiseRpm > 0 ? cruiseRpm.toFixed(0) : (cruiseFailureReason || 'N/A');
        
        const sfc = 0.5; // kg/kW-hr
        const fuelDensity = 0.8; // kg/L
        const fuelFlowKgHr = power_at_cruise_kw * sfc;
        const fuelFlowLph = fuelFlowKgHr / fuelDensity;
        document.getElementById('pp-lph-display').textContent = fuelFlowLph > 0 ? `${fuelFlowLph.toFixed(1)} L/hr` : (cruiseFailureReason || 'N/A');
        
        const fuelLiters = fuelWeight / fuelDensity;
        const enduranceHours = fuelLiters / fuelFlowLph;
        document.getElementById('fuel-liters-display').textContent = `${fuelLiters.toFixed(0)} L`;
        document.getElementById('fuel-hours-display').textContent = enduranceHours > 0 && isFinite(enduranceHours) ? `${enduranceHours.toFixed(1)} hrs` : (cruiseFailureReason || 'N/A');
        
        const range_km = (cruiseSpeed_kts * KTS_TO_MS) * enduranceHours * 3.6;
        document.getElementById('range-display').textContent = range_km > 0 && isFinite(range_km) ? `${range_km.toFixed(0)} km (${(range_km / 1.852).toFixed(0)} nm)` : (cruiseFailureReason || 'N/A');
    }

    // Propeller display
    const design_j = parseFloat(document.getElementById('prop-pitch-slider').value);
    const display_pitch_in = (propellerDiameter_m / 0.0254) * design_j;
    document.getElementById('pp-prop-display').textContent = `${(propellerDiameter_m * 39.37).toFixed(1)} x ${display_pitch_in.toFixed(1)}`;
}

// Main function to draw the flight envelope
function drawFlightEnvelope(geometrics, weights) {
    const { propellerDiameter_m, enginePower_kw, motorMaxRpm } = geometrics;
    const { mtow } = weights;

    const canvas = document.getElementById('flight-envelope-graph');
    const ctx = canvas.getContext('2d');
    const style = getComputedStyle(canvas);
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Constants
    const RHO_SL = 1.225;
    const KTS_TO_MS = 0.514444;
    const MS_TO_KTS = 1 / KTS_TO_MS;
    const HP_TO_W = 745.7;

    // Aircraft characteristics
    const aircraftWeight_n = mtow * 9.81;
    const stallSpeed_ias_kts = 45;
    const design_j = parseFloat(document.getElementById('prop-pitch-slider').value);
    const MAX_POWER_W = enginePower_kw * 1000;

    // Drag model
    const aspectRatio = parseFloat(document.getElementById('aspect-ratio').value);
    const oswaldEfficiency = 1.78 * (1 - 0.045 * Math.pow(aspectRatio, 0.68)) - 0.64;
    const wingArea_m2 = (geometrics.rootChord + geometrics.tipChord) * geometrics.semiSpan;
    const cd0 = 0.035;
    const k = 1 / (Math.PI * aspectRatio * oswaldEfficiency);

    // Analysis setup
    const alt_range_ft = Array.from({ length: 50 }, (_, i) => i * (40000 / 49));
    const tas_range_mps = Array.from({ length: 100 }, (_, i) => 10 + i * (140 / 99));
    
    // Determine RPM range based on powerplant type
    const powerplantType = document.getElementById('powerplant-type')?.value || 'fuel';
    let rpm_search_space, peak_power_rpm;
    
    if (powerplantType === 'electric' && motorMaxRpm) {
        // Electric motor: use motor-specific RPM range
        const min_rpm = motorMaxRpm * 0.2;
        const max_rpm = motorMaxRpm;
        peak_power_rpm = motorMaxRpm * 0.8;
        rpm_search_space = Array.from({ length: 200 }, (_, i) => min_rpm + i * ((max_rpm - min_rpm) / 199));
    } else {
        // Fuel engine: traditional RPM range
        rpm_search_space = Array.from({ length: 200 }, (_, i) => 1000 + i * (5000 / 199));
        peak_power_rpm = 5000;
    }

    let v_max_tas = [], v_min_tas = [], v_stall_tas = [];

    alt_range_ft.forEach(alt_ft => {
        const rho_alt = getIsaConditions(alt_ft);
        const power_derated_w = MAX_POWER_W * (rho_alt / RHO_SL);
        const engine_torque_curve = rpm_search_space.map(rpm => model_engine_torque(rpm, power_derated_w, peak_power_rpm));

        let thrust_available = tas_range_mps.map(tas_mps => {
            if (tas_mps === 0) return 0;
            const load_torques = rpm_search_space.map(rpm => model_prop_load_torque(rpm, tas_mps, propellerDiameter_m, design_j, rho_alt));
            
            let min_diff = Infinity, op_rpm_index = -1;
            for (let i = 0; i < rpm_search_space.length; i++) {
                const diff = Math.abs(engine_torque_curve[i] - load_torques[i]);
                if (diff < min_diff) {
                    min_diff = diff;
                    op_rpm_index = i;
                }
            }
            const op_rpm = rpm_search_space[op_rpm_index];
            const op_J = tas_mps / ((op_rpm / 60.0) * propellerDiameter_m);
            const { ct } = get_prop_coefficients(op_J, design_j);
            return ct * rho_alt * (op_rpm / 60.0)**2 * propellerDiameter_m**4;
        });

        let drag_required = tas_range_mps.map(v => {
            if (v === 0) return Infinity;
            const dynamic_pressure = 0.5 * rho_alt * v ** 2;
            const drag_parasite = dynamic_pressure * wingArea_m2 * cd0;
            const drag_induced = (k * aircraftWeight_n ** 2) / (dynamic_pressure * wingArea_m2);
            return drag_parasite + drag_induced;
        });

        const excess_thrust = thrust_available.map((t, i) => t - drag_required[i]);
        let intersections = [];
        for (let i = 0; i < excess_thrust.length - 1; i++) {
            if (Math.sign(excess_thrust[i]) !== Math.sign(excess_thrust[i + 1])) {
                intersections.push(i);
            }
        }

        if (intersections.length >= 2) {
            v_min_tas.push(tas_range_mps[intersections[0]]);
            v_max_tas.push(tas_range_mps[intersections[intersections.length - 1]]);
        } else {
            v_min_tas.push(NaN);
            v_max_tas.push(NaN);
        }

        const stall_tas_mps = (stallSpeed_ias_kts * KTS_TO_MS) / Math.sqrt(rho_alt / RHO_SL);
        v_stall_tas.push(stall_tas_mps);
    });

    // Plotting
    const v_min_tas_kts = v_min_tas.map(v => v * MS_TO_KTS);
    const v_max_tas_kts = v_max_tas.map(v => v * MS_TO_KTS);
    const v_stall_tas_kts = v_stall_tas.map(v => v * MS_TO_KTS);

    const low_speed_boundary = v_min_tas_kts.map((v, i) => Math.max(v, v_stall_tas_kts[i]));

    const max_alt = 40000;
    const max_tas = 140;

    function drawCurve(speeds, altitudes, color, lineWidth) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        let firstPoint = true;
        speeds.forEach((tas, i) => {
            if (!isNaN(tas)) {
                const x = (tas / max_tas) * w;
                const y = h - (altitudes[i] / max_alt) * h;
                if (firstPoint) {
                    ctx.moveTo(x, y);
                    firstPoint = false;
                } else {
                    ctx.lineTo(x, y);
                }
            }
        });
        ctx.stroke();
    }

    drawCurve(v_max_tas_kts, alt_range_ft, style.getPropertyValue('--max-speed-color'), style.getPropertyValue('--graph-line-width'));
    drawCurve(low_speed_boundary, alt_range_ft, style.getPropertyValue('--low-speed-color'), style.getPropertyValue('--graph-line-width'));

    // Draw axes
    ctx.strokeStyle = '#999';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h - 1);
    ctx.lineTo(w, h - 1);
    ctx.stroke();
    ctx.fillStyle = '#999';
    ctx.fillText('True Airspeed (kts)', w / 2 - 40, h - 5);

    ctx.save();
    ctx.translate(10, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Altitude (ft)', -20, 0);
    ctx.restore();


    // Fill the flight envelope
    ctx.beginPath();
    let first = true;
    v_max_tas_kts.forEach((tas, i) => {
        if (!isNaN(tas)) {
            const x = (tas / max_tas) * w;
            const y = h - (alt_range_ft[i] / max_alt) * h;
            if (first) {
                ctx.moveTo(x, y);
                first = false;
            } else {
                ctx.lineTo(x, y);
            }
        }
    });

    for (let i = low_speed_boundary.length - 1; i >= 0; i--) {
        const tas = low_speed_boundary[i];
        if (!isNaN(tas)) {
            const x = (tas / max_tas) * w;
            const y = h - (alt_range_ft[i] / max_alt) * h;
            ctx.lineTo(x, y);
        }
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 255, 255, 0.3)';
    ctx.fill();

}

function drawDragProfile(geometrics, weights) {
    const canvas = document.getElementById('drag-graph');
    const ctx = canvas.getContext('2d');
    const style = getComputedStyle(canvas);
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const RHO = 1.225;
    const KTS_TO_MS = 0.514444;
    const MS_TO_KTS = 1 / KTS_TO_MS;
    const LBF_TO_N = 4.44822;

    const wingArea = (geometrics.rootChord + geometrics.tipChord) * geometrics.semiSpan;
    const payloadArea = geometrics.payloadLength * geometrics.payloadWidth;
    const totalArea = wingArea + payloadArea;
    const aspectRatio = (geometrics.semiSpan * 2)**2 / wingArea;
    const e_oswald = 1.78 * (1 - 0.045 * Math.pow(aspectRatio, 0.68)) - 0.64;
    const cd_parasitic = 0.025 + 0.01 * (geometrics.payloadHeight * geometrics.payloadWidth) / totalArea;
    const k_induced = 1 / (Math.PI * aspectRatio * e_oswald);

    const max_speed_kts = 150;
    let speeds_kts = [], induced_drags = [], parasitic_drags = [], total_drags = [];
    for (let v_kts = 10; v_kts <= max_speed_kts; v_kts += 2) {
        const v_ms = v_kts * KTS_TO_MS;
        const cl = (weights.mtow * 9.81) / (0.5 * RHO * v_ms*v_ms * totalArea);
        const d_induced = k_induced * cl*cl * (0.5 * RHO * v_ms*v_ms * totalArea);
        const d_parasitic = cd_parasitic * (0.5 * RHO * v_ms*v_ms * totalArea);
        speeds_kts.push(v_kts);
        induced_drags.push(d_induced);
        parasitic_drags.push(d_parasitic);
        total_drags.push(d_induced + d_parasitic);
    }

    // --- Thrust Available Calculation for Multiple Altitudes ---
    const HP_SEA_LEVEL = geometrics.enginePower_kw * 1.34102;
    const design_j = parseFloat(document.getElementById('prop-pitch-slider').value);
    const altitudes_to_plot = [0, 10000, 25000]; // feet

    // Propeller efficiency curve that responds to pitch
    const prop_efficiency_curve = speeds_kts.map(v_kts => {
        // A simple model where efficiency depends on matching speed to pitch
        const speed_pitch_ratio = (v_kts * KTS_TO_MS) / (design_j * 25); // 25 is a scaling factor
        return 0.82 * Math.exp(-Math.pow(speed_pitch_ratio - 1, 2) / 0.5);
    });

    const thrust_curves_n = {};
    altitudes_to_plot.forEach(alt_ft => {
        const hp_at_altitude = degrade_power_for_altitude(HP_SEA_LEVEL, alt_ft);
        const density_ratio = get_air_density_ratio(alt_ft);
        const hp_curve = new Array(speeds_kts.length).fill(hp_at_altitude);
        const thrust_available_lbf = calculate_thrust_available(hp_curve, prop_efficiency_curve, density_ratio, speeds_kts);
        thrust_curves_n[alt_ft] = thrust_available_lbf.map(lbf => lbf * LBF_TO_N);
    });

    // Use original RPM-based thrust for other calculations to maintain UI consistency
    const { enginePower_kw, propellerDiameter_m, motorMaxRpm, motorKv } = geometrics;
    const MAX_POWER_W = enginePower_kw * 1000;
    
    // Determine RPM range based on powerplant type
    const powerplantType = document.getElementById('powerplant-type')?.value || 'fuel';
    let rpm_search_space, peak_power_rpm;
    
    if (powerplantType === 'electric' && motorMaxRpm) {
        // Electric motor: use motor-specific RPM range
        // Search from 20% to 100% of max RPM
        const min_rpm = motorMaxRpm * 0.2;
        const max_rpm = motorMaxRpm;
        peak_power_rpm = motorMaxRpm * 0.8; // Electric motors have flat power curves
        rpm_search_space = Array.from({length: 500}, (_, i) => min_rpm + i * ((max_rpm - min_rpm) / 499));
    } else {
        // Fuel engine: traditional 1000-6000 RPM range
        rpm_search_space = Array.from({length: 500}, (_, i) => 1000 + i * (5000 / 499));
        peak_power_rpm = 5000;
    }
    
    const engine_torque_curve = rpm_search_space.map(rpm => model_engine_torque(rpm, MAX_POWER_W, peak_power_rpm));
    let original_thrust_available = [];
    let operating_rpms = [];
    speeds_kts.forEach(v_kts => {
        const tas_mps = v_kts * KTS_TO_MS;
        const load_torques = rpm_search_space.map(rpm => model_prop_load_torque(rpm, tas_mps, propellerDiameter_m, design_j, RHO));
        let min_diff = Infinity, op_rpm_index = -1;
        for(let i=0; i < rpm_search_space.length; i++) {
            const diff = Math.abs(engine_torque_curve[i] - load_torques[i]);
            if (diff < min_diff) { min_diff = diff; op_rpm_index = i; }
        }
        const op_rpm = rpm_search_space[op_rpm_index];
        const op_J = tas_mps / ((op_rpm / 60.0) * propellerDiameter_m);
        const { ct } = get_prop_coefficients(op_J, design_j);
        const thrust = ct * RHO * (op_rpm/60.0)**2 * propellerDiameter_m**4;
        original_thrust_available.push(thrust);
        operating_rpms.push(op_rpm);
    });

    // --- Plotting ---
    const max_y = Math.max(...total_drags, ...original_thrust_available);

    function drawLine(data, color, is_dashed = false) {
        ctx.strokeStyle = color;
        ctx.lineWidth = style.getPropertyValue('--graph-line-width');
        ctx.setLineDash(is_dashed ? [5, 5] : []);
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = (speeds_kts[i] / max_speed_kts) * w;
            const y = h - (d / max_y) * h;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }
    
    function drawColoredLine(data, rpms) {
        const PEAK_POWER_RPM = 5000;
        const PEAK_TOLERANCE = 250;
        const colors = {
            lugging: '#0d6efd', // Blue
            peak: '#198754',    // Green
            redline: '#dc3545'  // Red
        };

        for (let i = 0; i < data.length - 1; i++) {
            const rpm = rpms[i];
            let color;
            if (rpm < PEAK_POWER_RPM - PEAK_TOLERANCE) {
                color = colors.lugging;
            } else if (rpm <= PEAK_POWER_RPM + PEAK_TOLERANCE) {
                color = colors.peak;
            } else {
                color = colors.redline;
            }
            
            ctx.strokeStyle = color;
            ctx.lineWidth = style.getPropertyValue('--graph-line-width');
            ctx.setLineDash([]);
            ctx.beginPath();
            const x1 = (speeds_kts[i] / max_speed_kts) * w;
            const y1 = h - (data[i] / max_y) * h;
            const x2 = (speeds_kts[i+1] / max_speed_kts) * w;
            const y2 = h - (data[i+1] / max_y) * h;
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }
    }

    drawLine(induced_drags, style.getPropertyValue('--induced-drag-color'));
    drawLine(parasitic_drags, style.getPropertyValue('--parasitic-drag-color'));
    drawLine(total_drags, style.getPropertyValue('--total-drag-color'));
    drawColoredLine(original_thrust_available, operating_rpms);
    
    // Draw the new thrust curves
    const thrust_curve_colors = ['#ff00ff', '#00ffff', '#ffff00']; // Magenta, Cyan, Yellow
    altitudes_to_plot.forEach((alt, i) => {
        drawLine(thrust_curves_n[alt], thrust_curve_colors[i]);
    });

    // --- Vertical Speed Lines ---
    const least_drag_index = total_drags.indexOf(Math.min(...total_drags));
    const best_glide_speed_kts = speeds_kts[least_drag_index];

    // Find cruise speed
    let cruise_speed_kts = 0;
    for (let i = least_drag_index; i < speeds_kts.length -1; i++) {
        if (original_thrust_available[i] > total_drags[i] && original_thrust_available[i+1] < total_drags[i+1]) {
            const t1 = original_thrust_available[i], d1 = total_drags[i];
            const t2 = original_thrust_available[i+1], d2 = total_drags[i+1];
            const v1 = speeds_kts[i], v2 = speeds_kts[i+1];
            const fraction = (d1 - t1) / ((d1 - t1) - (d2 - t2));
            cruise_speed_kts = v1 + fraction * (v2 - v1);
            break;
        }
    }

    const stall_speed_kts = Math.sqrt((weights.mtow * 9.81) / (0.5 * RHO * totalArea * 1.5)) / MS_TO_KTS;

    function drawVerticalLine(speed_kts, color, label) {
        const x = (speed_kts / max_speed_kts) * w;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 3]);
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
        ctx.fillStyle = color;
        ctx.save();
        ctx.translate(x + 5, h - 10);
        ctx.rotate(-Math.PI / 2);
        ctx.font = '10px sans-serif';
        ctx.fillText(`${label} (${speed_kts.toFixed(0)} kts)`, 0, 0);
        ctx.restore();
    }

    drawVerticalLine(stall_speed_kts, '#888888', 'Stall');
    drawVerticalLine(best_glide_speed_kts, '#888888', 'Best Glide');
    if (cruise_speed_kts > 0) {
        drawVerticalLine(cruise_speed_kts, '#888888', 'Cruise');
    }

    const best_glide_speed_ms = best_glide_speed_kts * KTS_TO_MS;
    const least_drag = 2 * cd_parasitic * (0.5 * RHO * best_glide_speed_ms**2 * totalArea);
    document.getElementById('best-glide-speed-display').textContent = `${(best_glide_speed_kts * 1.852).toFixed(0)} kmh (${best_glide_speed_kts.toFixed(0)} kts)`;
    document.getElementById('best-glide-drag-display').textContent = least_drag.toFixed(0);
    
    // Return original data to keep other UI elements consistent
    return { speeds_kts, total_drags, thrust_available: original_thrust_available, operating_rpms, best_glide_speed_kts };
}


export function performFlightEnvelopeAnalysis(geometrics, weights) {
    drawFlightEnvelope(geometrics, weights);
    const dragProfileData = drawDragProfile(geometrics, weights);
    performPowerplantAnalysis(geometrics, weights, dragProfileData);

    // Also perform the original aero analysis to keep other display values updated
    const RHO = 1.225; // Air density in kg/m^3
    const KTS_TO_MS = 0.514444;
    const MU = 1.81e-5; // Dynamic viscosity of air

    // 1. L/D Ratio Calculation
    const wingArea = (geometrics.rootChord + geometrics.tipChord) * geometrics.semiSpan;
    const payloadArea = geometrics.payloadLength * geometrics.payloadWidth;
    const totalArea = wingArea + payloadArea;
    const aspectRatio = (geometrics.semiSpan * 2) ** 2 / wingArea;

    // Simplified L/D calculation
    const e_oswald = 1.78 * (1 - 0.045 * Math.pow(aspectRatio, 0.68)) - 0.64;
    const cd_parasitic = 0.025 + 0.01 * (geometrics.payloadHeight * geometrics.payloadWidth) / totalArea;
    const cl_max_ld = Math.sqrt(cd_parasitic * Math.PI * aspectRatio * e_oswald);
    const ld_max = cl_max_ld / (2 * cd_parasitic);
    document.getElementById('ld-ratio-display').textContent = ld_max.toFixed(2);
    document.getElementById('oswald-eff-display').textContent = e_oswald.toFixed(3);

    // Update Wing Dimensions Display
    const fullSpan = geometrics.semiSpan * 2 + geometrics.payloadWidth;
    document.getElementById('wing-span-display').textContent = fullSpan.toFixed(2);
    document.getElementById('root-chord-display').textContent = geometrics.rootChord.toFixed(2);
    document.getElementById('tip-chord-display').textContent = geometrics.tipChord.toFixed(2);
    document.getElementById('wing-area-display').textContent = totalArea.toFixed(2);

    // 2. Takeoff Speed
    const cl_takeoff = 1.2; // Assume a reasonable CL for takeoff with flaps etc.
    const takeoff_lift = weights.mtow * 9.81 * 1.1;
    const takeoff_speed_ms = Math.sqrt(takeoff_lift / (0.5 * RHO * totalArea * cl_takeoff));
    const takeoff_speed_kts = takeoff_speed_ms / KTS_TO_MS;
    document.getElementById('takeoff-speed-display').textContent = `${(takeoff_speed_kts * 1.852).toFixed(0)} kmh (${takeoff_speed_kts.toFixed(0)} kts)`;

    // 3. Best Glide Speed
    const glide_speed_ms = Math.sqrt((2 * weights.mtow * 9.81) / (RHO * totalArea * cl_max_ld));
    const glide_speed_kts = glide_speed_ms / KTS_TO_MS;
    document.getElementById('glide-speed-display').textContent = `${(glide_speed_kts * 1.852).toFixed(0)} kmh (${glide_speed_kts.toFixed(0)} kts)`;

    // 4. Reynolds Number
    const mean_aerodynamic_chord = (geometrics.rootChord + geometrics.tipChord) / 2;
    const reynolds_number = (RHO * glide_speed_ms * mean_aerodynamic_chord) / MU;
    document.getElementById('reynolds-display').textContent = reynolds_number.toExponential(2);
}
