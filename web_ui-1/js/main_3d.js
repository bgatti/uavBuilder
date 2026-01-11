import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { calculateMetrics } from './physics_3d.js';
import { update3DScene, updatePieChart, updateSliderColors } from './ui.js';
import { performFlightEnvelopeAnalysis } from './analysis.js';
import { getMotorByThrust } from './motor.js';
import { calculateBatteryMetricsFromWeight } from './battery.js';

let scene, camera, renderer, controls;

function mainUpdateLoop() {
    const { geometrics, weights } = calculateMetrics();
    const powerplantType = document.getElementById('powerplant-type')?.value || 'fuel';
    update3DScene(scene, geometrics, weights);
    updatePieChart(weights, powerplantType);
    performFlightEnvelopeAnalysis(geometrics, weights);

    const targetWl = parseFloat(document.getElementById('target-wing-loading').value);
    const totalWingPlanformArea = weights.mtow / targetWl;
    const currentWl = weights.mtow / totalWingPlanformArea;

    // Update the display for actual wing loading
    const currentWlDisplay = document.getElementById('current-wl-display');
    if (currentWlDisplay) {
        currentWlDisplay.textContent = `${currentWl.toFixed(2)} kg/m²`;
    }
    updateSliderColors(targetWl, currentWl);
}

function init() {
    document.getElementById('aero-panel').style.display = 'block';
    document.getElementById('powerplant-panel').style.display = 'block';

    scene=new THREE.Scene();scene.background=new THREE.Color(0xa0a0a0);scene.fog=new THREE.Fog(0xa0a0a0,20,100);
    camera=new THREE.PerspectiveCamera(50,window.innerWidth/window.innerHeight,0.1,1000);camera.position.set(12,6,18);
    renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(window.innerWidth,window.innerHeight);document.body.appendChild(renderer.domElement);
    const h=new THREE.HemisphereLight(0xffffff,0x444444,2);h.position.set(0,20,0);scene.add(h);const d=new THREE.DirectionalLight(0xffffff,3);d.position.set(5,10,7.5);scene.add(d);
    const g=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshPhongMaterial({color:0x999999,depthWrite:false}));g.rotation.x=-Math.PI/2;scene.add(g);
    controls=new OrbitControls(camera,renderer.domElement);controls.target.set(3,0,0);
    
    document.querySelectorAll('input[type="range"]').forEach(s => {
        s.addEventListener('input', mainUpdateLoop);
    });

    // Add powerplant type selector listener
    const powerplantTypeSelect = document.getElementById('powerplant-type');
    if (powerplantTypeSelect) {
        powerplantTypeSelect.addEventListener('change', function() {
            togglePowerplantDisplay(this.value);
            mainUpdateLoop();
        });
        // Initialize display
        togglePowerplantDisplay(powerplantTypeSelect.value);
    }

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    mainUpdateLoop();
    (function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); })();
}

function togglePowerplantDisplay(powerplantType) {
    const fuelSection = document.getElementById('fuel-engine-section');
    const electricSection = document.getElementById('electric-motor-section');
    const fuelFractionLabel = document.getElementById('fuel-fraction-label');
    const powerLabel = document.getElementById('power-label');
    const energyLabel = document.getElementById('energy-label');
    
    if (powerplantType === 'electric') {
        if (fuelSection) fuelSection.style.display = 'none';
        if (electricSection) electricSection.style.display = 'block';
        if (fuelFractionLabel) fuelFractionLabel.textContent = 'Battery % of MTOW';
        if (powerLabel) powerLabel.textContent = 'Power Draw';
        if (energyLabel) energyLabel.textContent = 'Battery Energy';
    } else {
        if (fuelSection) fuelSection.style.display = 'block';
        if (electricSection) electricSection.style.display = 'none';
        if (fuelFractionLabel) fuelFractionLabel.textContent = 'Fuel % of MTOW';
        if (powerLabel) powerLabel.textContent = 'Fuel Burn';
        if (energyLabel) energyLabel.textContent = 'Fuel';
    }
}

init();
