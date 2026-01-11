import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { initParameterAnalysis, updateAnalysisGraph, getXAxisParam } from './parameter_analysis.js';
import { getMotorByThrust } from './motor.js';
import { getBatteryWeight, lookupClosestBattery, calculateBatteryMetrics, calculateBatteryMetricsFromWeight } from './battery.js';
import { lookupClosestMotor } from './motor.js';
import { formatWeight, formatPower } from './utils.js';
import {
    calculateAirframeWeight,
    AIRFRAME_COLOR,
    calculateMotorArmLength,
    calculateArmDiameter,
    getAirframeComponents
} from './airframe.js';
import { getBatteryDimensions, getPayloadDimensions, getCentralBodyDiameter } from './sizing.js';
import { calculateParasiticDrag, calculateInducedDrag, calculatePropellerThrust, calculatePowerAtSpeed, calculateEfficiencyKmPerKw } from './physics.js';

document.addEventListener('DOMContentLoaded', async function() {
    let scene, camera, renderer, copterGroup, controls;
    let droneData;

    async function loadDroneData() {
        const response = await fetch('drones.json');
        let rawDroneData = await response.json();
        // Process the data to add calculated fields
        droneData = rawDroneData.map(drone => {
            if (drone.MTOW_kg > 0 && drone.Max_Payload_kg >= 0) {
                const emptyWeight = drone.MTOW_kg - drone.Max_Payload_kg;
                // Estimate battery weight as 40% of empty weight
                const batteryWeight = emptyWeight * 0.4;
                drone['battery-weight-percent'] = (batteryWeight / drone.MTOW_kg) * 100;
            }
            return drone;
        });
    }

    function initThreeJS() {
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x000000);
        scene.fog = new THREE.Fog(0x000000, 20, 100);

        camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 2, 8);

        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);

        const h = new THREE.HemisphereLight(0xffffff, 0x444444, 2);
        h.position.set(0, 20, 0);
        scene.add(h);

        const d = new THREE.DirectionalLight(0xffffff, 3);
        d.position.set(5, 10, 7.5);
        scene.add(d);

        controls = new OrbitControls(camera, renderer.domElement);
        controls.target.set(0, 1, 0);

        copterGroup = new THREE.Group();
        scene.add(copterGroup);

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        animate();
    }


    function centerObjectInView() {
        // Calculate bounding box of the copter group
        const box = new THREE.Box3().setFromObject(copterGroup);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        // Update orbit controls target to center of object
        controls.target.copy(center);
        
        // Calculate camera distance based on bounding box size
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = camera.fov * (Math.PI / 180); // Convert vertical FOV to radians
        const cameraDistance = maxDim / 2 / Math.tan(fov / 2);
        
        // Position camera with some offset
        const offset = size.length();
        camera.position.set(
            center.x + offset * 0.7,
            center.y + maxDim * 0.5,
            center.z + cameraDistance * 1.2
        );
        
        controls.update();
    }

    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }

    function renderMultiCopter(numMotors, batteryWeight, payloadWeight, motor, propDiameter) {
        while (copterGroup.children.length) copterGroup.remove(copterGroup.children[0]);

        const WEIGHT_COLORS = {
            payload: new THREE.Color('#36a2eb'),
            battery: new THREE.Color('#ffcd56'),
            powerplant: new THREE.Color('#ff6384'),
            airframe: new THREE.Color(AIRFRAME_COLOR)
        };

        const batteryDimensions = getBatteryDimensions(batteryWeight);
        const payloadDimensions = getPayloadDimensions(payloadWeight);
        const bodyDiameter = getCentralBodyDiameter(batteryDimensions, payloadDimensions);
        const motorHeight = motor ? motor.height_m : 0.05;
        const radius = bodyDiameter / 2;
        const bodyY = 0; // Center frame at Y=0

        const shape = new THREE.Shape();
        for (let i = 0; i < numMotors; i++) {
            const angle = (i / numMotors) * Math.PI * 2;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            if (i === 0) shape.moveTo(x, y);
            else shape.lineTo(x, y);
        }
        shape.closePath();

        const extrudeSettings = { depth: motorHeight, bevelEnabled: false };
        const bodyGeom = new THREE.ExtrudeGeometry(shape, extrudeSettings);
        const bodyMat = new THREE.MeshPhongMaterial({ color: WEIGHT_COLORS.airframe });
        const body = new THREE.Mesh(bodyGeom, bodyMat);
        body.rotation.x = -Math.PI / 2;
        body.position.y = bodyY - motorHeight / 2;
        copterGroup.add(body);

        for (let i = 0; i < numMotors; i++) {
            const angle = (2 * Math.PI * i) / numMotors;
            const motorDistance = (bodyDiameter / 2) + (propDiameter / 2) + 0.05; // margin
            const armLen = motorDistance - (bodyDiameter / 2);
            let armDiameter = motor && motor.diameter_m > 0 && motor.height_m > 0 ?
                (motor.height_m + motor.diameter_m) / 3 : 0.04;
            if (!armDiameter || isNaN(armDiameter) || armDiameter <= 0) armDiameter = 0.02;

            const x = Math.cos(angle) * motorDistance;
            const z = Math.sin(angle) * motorDistance;

            // Arm
            try {
                if (armLen > 0 && armDiameter > 0) {
                    const armGeom = new THREE.CylinderGeometry(armDiameter / 2, armDiameter / 2, armLen, 16);
                    const armMat = new THREE.MeshPhongMaterial({ color: AIRFRAME_COLOR });
                    const arm = new THREE.Mesh(armGeom, armMat);
                    arm.position.set(Math.cos(angle) * (radius + armLen / 2), 0, Math.sin(angle) * (radius + armLen / 2));
                    arm.rotation.z = Math.PI / 2;
                    arm.rotation.y = -angle;
                    copterGroup.add(arm);
                }
            } catch (err) {
                console.error('Error rendering arm', { armLen, armDiameter, x, z }, err);
                throw err;
            }

            // Motor
            try {
                if (motor && motor.diameter_m > 0 && motor.height_m > 0) {
                    const motorGeom = new THREE.CylinderGeometry(motor.diameter_m / 2, motor.diameter_m / 2, motor.height_m, 16);
                    const motorMat = new THREE.MeshPhongMaterial({ color: WEIGHT_COLORS.powerplant });
                    const motorMesh = new THREE.Mesh(motorGeom, motorMat);
                    motorMesh.position.set(x, bodyY + motor.height_m / 2, z);
                    copterGroup.add(motorMesh);
                }
            } catch (err) {
                console.error('Error rendering motor', { motor, x, z }, err);
            }

            // Propeller
            try {
                if (propDiameter > 0 && !isNaN(propDiameter)) {
                    const propGeom = new THREE.CylinderGeometry(propDiameter / 2, propDiameter / 2, 0.02, 32);
                    const propMat = new THREE.MeshBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.5 });
                    const prop = new THREE.Mesh(propGeom, propMat);
                    prop.position.set(x, bodyY + motorHeight + 0.01, z);
                    prop.rotation.y = Math.PI / 2;
                    copterGroup.add(prop);
                }
            } catch (err) {
                console.error('Error rendering propeller', { propDiameter, x, z }, err);
            }
        }
        // Render payload (center)
        try {
            if (payloadWeight > 0) {
                const payloadDims = getPayloadDimensions(payloadWeight);
                const payloadGeom = new THREE.BoxGeometry(payloadDims.width, payloadDims.height, payloadDims.depth);
                const payloadMat = new THREE.MeshPhongMaterial({ color: WEIGHT_COLORS.payload });
                const payloadMesh = new THREE.Mesh(payloadGeom, payloadMat);
                payloadMesh.position.set(0, bodyY - motorHeight / 2 - payloadDims.height / 2, 0); // Below frame
                copterGroup.add(payloadMesh);
            }
        } catch (err) {
            console.error('Error rendering payload', { payloadWeight }, err);
        }

        // Render battery (center, offset)
        try {
            if (batteryWeight > 0) {
                const batteryDims = getBatteryDimensions(batteryWeight);
                const batteryGeom = new THREE.BoxGeometry(batteryDims.width, batteryDims.height, batteryDims.depth);
                const batteryMat = new THREE.MeshPhongMaterial({ color: WEIGHT_COLORS.battery });
                const batteryMesh = new THREE.Mesh(batteryGeom, batteryMat);
                batteryMesh.position.set(0, bodyY + motorHeight / 2 + batteryDims.height / 2, 0); // Above frame
                copterGroup.add(batteryMesh);
            }
        } catch (err) {
            console.error('Error rendering battery', { batteryWeight }, err);
        }
        
        // Auto-center the view on the rendered object
        centerObjectInView();
    }

    function updateMultiCopterMetrics(hoverParameter) {
        // Get input values first
        const numMotors = parseInt(document.getElementById('num-motors-slider').value);
        const batteryWeightPercent = parseFloat(document.getElementById('battery-weight-percent-slider').value);
        const diskLoading = parseFloat(document.getElementById('disk-loading-slider').value);
        const propPitch = parseFloat(document.getElementById('prop-pitch-slider').value);
        const numBlades = parseInt(document.getElementById('num-blades-slider').value);
        const payloadG = parseFloat(document.getElementById('payload-slider').value);
        const twRatio = parseFloat(document.getElementById('t-w-ratio-slider').value);

        const setText = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.innerText = value;
        };

        // Declare variables that will be calculated
        let motor, propDiameter, batteryMetrics, airframeWeight;
        let requiredCRating = 0;
        const batteryVoltage = 22.2; // Assume 6S
    setText('num-motors-display', numMotors);
    setText('battery-weight-percent-display', `${batteryWeightPercent.toFixed(0)}`);
    setText('disk-loading-display', `${diskLoading.toFixed(0)}`);
    setText('prop-pitch-display', propPitch.toFixed(2));
    setText('num-blades-display', numBlades);
    setText('payload-display', payloadG);
    setText('t-w-ratio-display', twRatio.toFixed(1));

        const payloadKg = payloadG / 1000;
        
        const currentUAV = {
            name: 'current',
            'num-motors': numMotors,
            'battery-weight-percent': batteryWeightPercent,
            'disk-loading': diskLoading,
            'prop-pitch': propPitch,
            'num-blades': numBlades,
            'payload': payloadG,
            't-w-ratio': twRatio,
        };

        const maxedOutList = document.getElementById('maxed-out-list');
        maxedOutList.innerHTML = '';
        const maxedOutParams = new Set();

        const maxThrust = Math.max(...droneData.map(d => d.MTOW_kg * 9.81 * 2));
        const maxPropDia = Math.max(...droneData.map(d => d.Prop_Dia_in)) * 0.0254;

        // Initialize mtow with a reasonable starting estimate
        let mtow = payloadKg > 0 ? payloadKg * 4 : 1.0; // Start with payload * 4, or 1kg if payload is zero
        let warning = '';
        console.log('updateMultiCopterMetrics input:', {
            numMotors,
            batteryWeightPercent,
            diskLoading,
            propPitch,
            payloadG,
            twRatio
        });
        console.log('payloadKg:', payloadKg);
        console.log('Initial mtow:', mtow);
        let thrustRequired = 0;
        let currentBatteryWeight = mtow * (batteryWeightPercent / 100);

        for (let i = 0; i < 100; i++) {
            // Explicitly link thrust-to-weight ratio to required thrust
            thrustRequired = mtow * 9.81 * twRatio;
            console.log('Iteration', i, 'mtow:', mtow, 'thrustRequired:', thrustRequired);
            if (thrustRequired > maxThrust) {
                thrustRequired = maxThrust;
                warning = `Selected thrust-to-weight ratio (${twRatio}) is not achievable with available motors. Max possible: ${(maxThrust / (mtow * 9.81)).toFixed(2)}`;
                if (!maxedOutParams.has('Max Thrust')) {
                    maxedOutParams.add('Max Thrust');
                    maxedOutList.innerHTML += `<li>Max Thrust: ${(maxThrust / 9.81).toFixed(2)} kgf</li>`;
                }
            }
            const thrustPerMotor = thrustRequired / numMotors;
            
            // Estimate propeller diameter from disk loading and thrust per motor
            // Disk Loading (DL) = Thrust / Area => Area = Thrust / DL => D = 2 * sqrt(Thrust / (DL * pi))
            let estimatedPropDiameter = 0.2; // Default fallback (meters)
            if (diskLoading > 0 && thrustPerMotor > 0) {
                const area = thrustPerMotor / diskLoading;
                estimatedPropDiameter = 2 * Math.sqrt(area / Math.PI);
            }
            // Clamp to reasonable range (10cm to 2m)
            if (isNaN(estimatedPropDiameter) || estimatedPropDiameter < 0.1 || estimatedPropDiameter > 2.0) {
                estimatedPropDiameter = 0.2;
            }
            propDiameter = estimatedPropDiameter;
            
            console.log('thrustPerMotor:', thrustPerMotor);
            console.log('Motor calculation input:', { thrustPerMotor, diskLoading, propDiameter });
            
            motor = getMotorByThrust(thrustPerMotor, diskLoading, propDiameter);
            
            console.log('Motor calculation output:', motor);
            
            // Defensive checks for motor validity
            let motorValid = motor && !isNaN(motor.thrust_N) && isFinite(motor.thrust_N) && motor.thrust_N > 0 && !isNaN(motor.power_W) && isFinite(motor.power_W) && motor.power_W > 0 && !isNaN(motor.max_rpm) && isFinite(motor.max_rpm) && motor.max_rpm > 0;
            if (!motorValid) {
                console.warn('Motor is invalid or missing. Proceeding with calculated motor for rendering and analysis.', motor);
            }
            
            // Use fallback efficiency if motor is invalid
            const motorEfficiency = motor && motor.efficiency ? motor.efficiency : 0.7;
            const powerRequired = thrustPerMotor * numMotors / motorEfficiency;
            
            // Iteratively find battery that meets weight target
            const newTargetBatteryWeight = mtow * (batteryWeightPercent / 100);
            currentBatteryWeight += (newTargetBatteryWeight - currentBatteryWeight) * 0.1; // Slow iteration
            
            // Estimate C-Rating based on power draw and a starting capacity guess
            let estimatedCapacity = currentBatteryWeight / 0.2; // Rough guess: 200g/Ah
            requiredCRating = (powerRequired / batteryVoltage) / (estimatedCapacity > 0 ? estimatedCapacity : 1);

            batteryMetrics = calculateBatteryMetricsFromWeight(currentBatteryWeight, batteryVoltage, requiredCRating);
            
            // Use the new physics-based airframe weight calculation
            let motorWeight = motor && motor.weight_kg ? motor.weight_kg : 0;
            airframeWeight = calculateAirframeWeight(mtow);
            
            // Defensive logging for newMtow calculation
            // Estimate airframeWeight as 25% of mtow if undefined or NaN
            if (typeof airframeWeight === 'undefined' || isNaN(airframeWeight)) {
                airframeWeight = 0.25 * mtow;
                console.log('Estimating airframeWeight as 25% of mtow:', airframeWeight);
            }
            
            // Calculate new MTOW using battery metrics
            let newMtow = payloadKg + batteryMetrics.weight + (motorWeight * numMotors) + airframeWeight;
            if ([payloadKg, batteryMetrics.weight, motorWeight, numMotors, airframeWeight].some(val => isNaN(val))) {
                console.error('NaN detected in newMtow calculation. Breaking loop.', {
                    payloadKg,
                    batteryWeight: batteryMetrics.weight,
                    motorWeight,
                    numMotors,
                    airframeWeight
                });
                break;
            }
            if (Math.abs(newMtow - mtow) < 0.01) {
                mtow = newMtow;
                break;
            }
            mtow += (newMtow - mtow) * 0.1; // Slow damping factor
        }
        
        // Show/hide maxed out parameters panel based on whether there are any
        const maxedOutPanel = document.getElementById('maxed-out-panel');
        if (maxedOutPanel) {
            maxedOutPanel.style.display = maxedOutParams.size > 0 ? 'block' : 'none';
        }
        // Show warning if thrust-to-weight ratio is not achievable
        const warningDiv = document.getElementById('tw-warning');
        if (warningDiv) {
            warningDiv.innerText = warning;
            warningDiv.style.display = warning ? 'block' : 'none';
        }

        const powerToHover = mtow * 9.81 * 10; // Simplified power calculation
        const energyWh = batteryMetrics.energy_Wh;
        const durationMinutes = (energyWh / (powerToHover * 1.5)) * 60 * 0.75; // at 75% power with 1.5x hover power draw

        const airframe = { bodyDiameter: getCentralBodyDiameter(getBatteryDimensions(batteryMetrics.weight), getPayloadDimensions(payloadKg)) };
        const battery = { ...getBatteryDimensions(batteryMetrics.weight) };
        const payload = { ...getPayloadDimensions(payloadKg) };

        let maxSpeed = 0;
        let cruiseSpeed = 0;
        let maxEfficiency = 0;
        let peakEfficiencySpeed = 0;
        let enduranceRange = 0;

        for (let speed = 1; speed < 112; speed += 1) {
            const drag = calculateParasiticDrag(speed, airframe, battery, payload);
            const powerForDrag = drag * speed;
            const totalPower = (powerToHover + powerForDrag) / 0.8; // 80% efficiency
            if (totalPower < motor.power_W * numMotors) {
                maxSpeed = speed;
                if (totalPower < motor.power_W * numMotors * 0.75) {
                    cruiseSpeed = speed;
                }
            } else {
                break;
            }
        }

        // Calculate efficiency at various speeds
        const efficiencyData = [];
        for (let speed = 0.1; speed <= 20; speed += 0.25) {
            const power = calculatePowerAtSpeed(speed, mtow, airframe, battery, payload, powerToHover);
            const efficiency = calculateEfficiencyKmPerKw(speed, power);
            if (efficiency > 0) {
                efficiencyData.push({ speed, efficiency, power });
                
                if (efficiency > maxEfficiency) {
                    maxEfficiency = efficiency;
                    peakEfficiencySpeed = speed;
                }
            }
        }
        
        // Calculate endurance (range at cruise speed)
        if (cruiseSpeed > 0) {
            const cruisePower = calculatePowerAtSpeed(cruiseSpeed, mtow, airframe, battery, payload, powerToHover);
            const enduranceHours = (batteryMetrics.energy_Wh / cruisePower) * 0.75; // 75% usable
            const cruiseSpeedKmh = cruiseSpeed * 3.6;
            enduranceRange = enduranceHours * cruiseSpeedKmh;
        }

        setText('duration-display', `${durationMinutes.toFixed(1)} min`);
        setText('max-efficiency-display', `${(maxEfficiency || 0).toFixed(2)} km/kW`);
        setText('peak-speed-display', `${(peakEfficiencySpeed || 0).toFixed(1)} m/s`);
        setText('endurance-display', `${(enduranceRange || 0).toFixed(2)} km`);
        setText('max-speed-display', `${maxSpeed.toFixed(1)} m/s`);
        setText('cruise-speed-display', `${cruiseSpeed.toFixed(1)} m/s`);

    setText('mtow-display', `${mtow.toFixed(2)} kg`);

    // Lookup closest real-world battery and motor models
    // Calculate required mAh and required power for battery lookup
    const required_mAh = batteryMetrics.capacity * 1000;
    const required_power_W = numMotors * (motor && motor.power_W ? motor.power_W : 0);
    let closestMotor = lookupClosestMotor(motor && motor.power_W ? motor.power_W : 0, motor && motor.max_rpm ? motor.max_rpm : 0, motor && motor.thrust_N ? motor.thrust_N : 0);
    if (!closestMotor) {
        closestMotor = { Model: 'Not Found', Power_W: '-', max_rpm: '-', Weight_kg: '-', thrust_N: '-', kv: '-' };
    }
        const closestBattery = lookupClosestBattery(required_mAh, required_power_W);
        console.log('Closest Battery Model:', closestBattery);
        if (closestMotor) {
            console.log('Closest Motor Model:', closestMotor);
        } else {
            console.warn('Closest Motor Model: null');
            console.warn('lookupClosestMotor parameters:', {
                power_W: motor.power_W,
                max_rpm: motor.max_rpm
            });
        }
        // Display closest battery and motor model names in UI
        setText('battery-model-display', closestBattery ? closestBattery.Model : '-');
        setText('motor-model-display', closestMotor ? closestMotor.Model : '-');
        // Optionally display more specs if desired
        setText('battery-capacity-spec-display', batteryMetrics.capacity ? `${batteryMetrics.capacity.toFixed(2)} Ah` : '-');
        setText('battery-voltage-spec-display', closestBattery ? `${closestBattery.Voltage_V} V` : '-');

        const aeroPanel = document.getElementById('aero-panel');
        if (aeroPanel) {
            const tipSpeed = (motor.max_rpm / 60) * Math.PI * propDiameter;
            const aeroSpans = aeroPanel.querySelectorAll('span');
            if (aeroSpans[0]) aeroSpans[0].innerText = `${diskLoading.toFixed(0)} N/m²`;
            if (aeroSpans[1]) aeroSpans[1].innerText = `${(propDiameter * 100).toFixed(1)} cm`;
            if (aeroSpans[2]) aeroSpans[2].innerText = `${tipSpeed.toFixed(0)} m/s`;
            if (aeroSpans[3]) aeroSpans[3].innerText = `${maxEfficiency.toFixed(2)} km/kW`;
            if (aeroSpans[4]) aeroSpans[4].innerText = `${peakEfficiencySpeed.toFixed(1)} m/s`;
            if (aeroSpans[5]) aeroSpans[5].innerText = `${enduranceRange.toFixed(2)} km`;
        }

        // Update UI with battery metrics from the consolidated calculation
        const motorSize = motor && motor.diameter_m > 0 && motor.height_m > 0 ? `${(motor.diameter_m*100).toFixed(1)} x ${(motor.height_m*100).toFixed(1)} mm` : '-';
        const propSize = propDiameter > 0 ? `${(propDiameter*100).toFixed(1)} cm` : '-';
        
        const batteryDims = getBatteryDimensions(batteryMetrics.weight);
        const payloadDims = getPayloadDimensions(payloadKg);

        // Update battery-related UI elements using batteryMetrics
        setText('battery-volume-display', `${batteryMetrics.volume_L.toFixed(2)} L`);
        setText('battery-size-display', `${(batteryDims.width * 100).toFixed(1)}x${(batteryDims.height * 100).toFixed(1)}x${(batteryDims.depth * 100).toFixed(1)} cm`);
        setText('battery-energy-density-display', `${batteryMetrics.batteryEnergyDensity.toFixed(1)} Wh/L`);
        setText('payload-size-display', `${(payloadDims.width * 100).toFixed(1)}x${(payloadDims.height * 100).toFixed(1)}x${(payloadDims.depth * 100).toFixed(1)} cm`);
        setText('motor-size-display', motorSize);
        setText('prop-size-display', propSize);

        // Show battery and motor size/energy density in Powerplant Analysis panel
        const powerPanel = document.getElementById('powerplant-panel');
        if (powerPanel) {
            const batteryDims = getBatteryDimensions(batteryMetrics.weight);
            let batteryInfo = '';
            batteryInfo += `<div>Energy Density: ${batteryMetrics.batteryEnergyDensity.toFixed(1)} Wh/L</div>`;
            batteryInfo += `<div>Size: ${(batteryDims.width * 100).toFixed(1)}x${(batteryDims.height * 100).toFixed(1)}x${(batteryDims.depth * 100).toFixed(1)} cm</div>`;
            let motorInfo = '';
            motorInfo += `<div>Size: ${motor && motor.diameter_m > 0 && motor.height_m > 0 ? `${(motor.diameter_m*100).toFixed(1)} x ${(motor.height_m*100).toFixed(1)} mm` : '-'}</div>`;
            // Append to existing panel content
            const batteryPanel = powerPanel.querySelector('.battery-specs');
            if (batteryPanel) batteryPanel.innerHTML += batteryInfo;
            const motorPanel = powerPanel.querySelector('.motor-specs');
            if (motorPanel) motorPanel.innerHTML += motorInfo;
        }

        const staticThrust = motor && typeof motor.thrust_N === 'number' ? motor.thrust_N : 0;
        const motorRpm = motor && typeof motor.max_rpm === 'number' ? Math.round(motor.max_rpm / 100) * 100 : 0;
        setText('voltage-display', `${batteryVoltage && !isNaN(batteryVoltage) ? batteryVoltage.toFixed(1) : '-'} V`);
        setText('motor-diameter-display', motor && typeof motor.diameter_m === 'number' && !isNaN(motor.diameter_m) ? `${(motor.diameter_m * 1000).toFixed(1)} mm` : '-');
        setText('motor-power-display', motor && typeof motor.power_W === 'number' && !isNaN(motor.power_W) ? formatPower(motor.power_W) : '-');
        setText('motor-kv-display', motor && typeof motor.kv === 'number' && !isNaN(motor.kv) ? motor.kv.toFixed(0) : '-');
        setText('motor-rpm-display', motorRpm && !isNaN(motorRpm) ? `${motorRpm.toFixed(0)} RPM` : '-');
        setText('motor-weight-display', motor && typeof motor.weight_kg === 'number' && !isNaN(motor.weight_kg) ? formatWeight(motor.weight_kg) : '-');
        setText('static-thrust-display', `${staticThrust.toFixed(2)} N (${(staticThrust * 101.97).toFixed(0)} g)`);
        const totalThrust = staticThrust * numMotors;
        setText('total-thrust-display', `${totalThrust.toFixed(2)} N (${(totalThrust * 101.97).toFixed(0)} g)`);
        setText('battery-weight-display', batteryMetrics.weight && !isNaN(batteryMetrics.weight) ? formatWeight(batteryMetrics.weight) : '-');
        setText('battery-c-rating-display', `Required: ${requiredCRating && !isNaN(requiredCRating) ? requiredCRating.toFixed(1) : '-'}C, Closest: ${batteryMetrics.cRating && !isNaN(batteryMetrics.cRating) ? batteryMetrics.cRating.toFixed(1) : '-'}C`);

        updateWeightBreakdownChart({
            payload: payloadKg,
            battery: batteryMetrics.weight,
            powerplant: motor.weight_kg * numMotors,
            airframe: airframeWeight,
        });

        console.log('TRACE: batteryWeight before renderMultiCopter:', batteryMetrics.weight);
        renderMultiCopter(numMotors, batteryMetrics.weight, payloadKg, motor, propDiameter);
        updateEfficiencyGraph(powerToHover, mtow, airframe, battery, payload);
        currentUAV['max-speed'] = maxSpeed;
        currentUAV['cruise-speed'] = cruiseSpeed;
        currentUAV['mtow'] = mtow;
        currentUAV['duration'] = durationMinutes;
        currentUAV['prop-diameter'] = propDiameter;
        currentUAV['tip-speed'] = (motor.max_rpm / 60) * Math.PI * propDiameter;
        currentUAV['max-efficiency'] = maxEfficiency;
        currentUAV['cruise-efficiency'] = cruiseEfficiency;
        currentUAV['endurance-range'] = enduranceRange;
        currentUAV['thrust-required'] = thrustRequired;
        
        // Add all slider values to currentUAV
        document.querySelectorAll('.slider-group input[type="range"]').forEach(slider => {
            const key = slider.id.replace('-slider', '');
            currentUAV[key] = parseFloat(slider.value);
        });

        updateAnalysisGraph(getXAxisParam(), droneData, currentUAV);
    }


    function updateEfficiencyGraph(powerToHover, mtow, airframe, battery, payload) {
        const canvas = document.getElementById('efficiency-graph');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        // Calculate efficiency curve over speed range
        const efficiencyData = [];
        let maxEfficiency = 0;
        const maxSpeed = 25; // m/s
        
        for (let speed = 0.5; speed < maxSpeed; speed += 0.5) {
            const power = calculatePowerAtSpeed(speed, mtow, airframe, battery, payload, powerToHover);
            const efficiency = calculateEfficiencyKmPerKw(speed, power);
            efficiencyData.push({ speed, efficiency });
            if (efficiency > maxEfficiency) {
                maxEfficiency = efficiency;
            }
        }

        // Helper function for nice grid lines
        function getNiceGrid(maxVal, numLinesApprox = 5) {
            if (maxVal === 0 || !isFinite(maxVal)) return { step: 1, lines: [] };
            const stepApprox = maxVal / numLinesApprox;
            if (stepApprox === 0 || !isFinite(stepApprox)) return { step: 1, lines: [] };
            const magnitude = Math.pow(10, Math.floor(Math.log10(stepApprox)));
            const residual = stepApprox / magnitude;

            let niceResidual;
            const niceOptions = [1, 2, 5, 10];
            let minDiff = Infinity;
            for (const opt of niceOptions) {
                const diff = Math.abs(residual - opt);
                if (diff < minDiff) {
                    minDiff = diff;
                    niceResidual = opt;
                }
            }
            
            const step = niceResidual * magnitude;
            
            const lines = [];
            for (let i = step; i <= maxVal; i += step) {
                lines.push(i);
            }
            return { step, lines };
        }

        // Draw grid lines and labels
        ctx.strokeStyle = '#444';
        ctx.fillStyle = '#cccccc';
        ctx.font = '11px sans-serif';

        // Y-axis (Efficiency in km/kW)
        const yGrid = getNiceGrid(maxEfficiency * 1.1);
        yGrid.lines.forEach(line => {
            const y = h - (line / (maxEfficiency * 1.1)) * h;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
            ctx.fillText(line.toFixed(1), 5, y - 5);
        });

        // X-axis (Speed in m/s)
        const xGrid = getNiceGrid(maxSpeed);
        xGrid.lines.forEach(line => {
            const x = (line / maxSpeed) * w;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.stroke();
            ctx.fillText(line.toFixed(0), x + 5, h - 5);
        });

        // Draw efficiency curve
        ctx.strokeStyle = '#ffc107'; // Vertex accent gold
        ctx.lineWidth = 3;
        ctx.beginPath();
        for (let i = 0; i < efficiencyData.length; i++) {
            const { speed, efficiency } = efficiencyData[i];
            const x = (speed / maxSpeed) * w;
            const y = h - (efficiency / (maxEfficiency * 1.1)) * h;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Draw labels
        ctx.fillStyle = '#cccccc';
        ctx.font = 'bold 13px sans-serif';
        ctx.fillText('Efficiency (km/kW) vs Speed', 10, 25);
        ctx.font = '11px sans-serif';
        ctx.fillText('Y-axis: km/kW', 10, h - 10);
        ctx.fillText('X-axis: Speed (m/s)', w - 200, h - 10);

        // Mark peak efficiency
        const peakIdx = efficiencyData.findIndex(d => d.efficiency === maxEfficiency);
        if (peakIdx >= 0) {
            const { speed, efficiency } = efficiencyData[peakIdx];
            const x = (speed / maxSpeed) * w;
            const y = h - (efficiency / (maxEfficiency * 1.1)) * h;
            ctx.fillStyle = '#ffd700'; // Brighter gold for peak
            ctx.beginPath();
            ctx.arc(x, y, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#ffc107';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.fillStyle = '#ffc107';
            ctx.font = 'bold 11px sans-serif';
            ctx.fillText(`Peak: ${maxEfficiency.toFixed(2)}`, x + 10, y - 15);
        }
    }


    function updateWeightBreakdownChart(weights) {
        const pieChart = document.getElementById('pie-chart');
        const legend = document.getElementById('legend');
        let gradientString = 'conic-gradient(';
        let currentAngle = 0;
        legend.innerHTML = ''; // Clear old legend

        const WEIGHT_COLORS = {
            payload: '#36a2eb',
            battery: '#ffcd56',
            powerplant: '#ff6384',
            airframe: AIRFRAME_COLOR
        };

        const totalWeight = ['payload', 'battery', 'powerplant', 'airframe'].map(k => weights[k]).reduce((a, b) => a + (b && !isNaN(b) ? b : 0), 0);
        for (const [name, weight] of Object.entries(weights)) {
            if (!weight || isNaN(weight) || weight <= 0) continue;
            const percentage = totalWeight > 0 ? (weight / totalWeight) * 100 : 0;
            const color = WEIGHT_COLORS[name];
            gradientString += `${color} ${currentAngle.toFixed(2)}deg ${(currentAngle + percentage * 3.6).toFixed(2)}deg, `;
            currentAngle += percentage * 3.6;
            legend.innerHTML += `<div class="legend-item"><div class="legend-color" style="background-color:${color};"></div>${name.charAt(0).toUpperCase() + name.slice(1)}: ${weight.toFixed(2)} kg (${percentage.toFixed(1)}%)</div>`;
        }
        pieChart.style.background = gradientString.slice(0, -2) + ')';
    }

    document.querySelectorAll('input[type="range"]').forEach(slider => {
        slider.addEventListener('input', () => updateMultiCopterMetrics());
    });

    loadDroneData().then(() => {
        initThreeJS();
        initParameterAnalysis(droneData, updateMultiCopterMetrics);
        updateMultiCopterMetrics();
    });
});
