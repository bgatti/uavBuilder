import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { calculateMetrics } from './physics.js';
import { update3DScene, updatePieChart, updateSliderColors } from './ui.js';
import { performFlightEnvelopeAnalysis } from './analysis.js';

let scene, camera, renderer, controls;

function mainUpdateLoop() {
    const { geometrics, weights } = calculateMetrics();
    update3DScene(scene, geometrics, weights);
    updatePieChart(weights);
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

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    mainUpdateLoop();
    (function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); })();
}

init();
