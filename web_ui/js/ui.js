import * as THREE from 'three';
import { WEIGHT_COLORS, generateNaca4Airfoil } from './utils.js';

let leftWingMesh, rightWingMesh, payloadMesh, motorMesh, propMesh, cmMesh, linesMesh, cpMesh, wingbodyMesh, leftFuelMesh, rightFuelMesh;

export function updatePieChart(weights) {
    const pieChart = document.getElementById('pie-chart');
    const legend = document.getElementById('legend');
    let gradientString = 'conic-gradient(';
    let currentAngle = 0;
    legend.innerHTML = ''; // Clear old legend

    for (const [name, weight] of Object.entries(weights)) {
        if (name === 'mtow') continue;
        const percentage = (weight / weights.mtow) * 100;
        const color = WEIGHT_COLORS[name];

        gradientString += `${color} ${currentAngle.toFixed(2)}deg ${(currentAngle + percentage * 3.6).toFixed(2)}deg, `;
        currentAngle += percentage * 3.6;

        legend.innerHTML += `<div class="legend-item"><div class="legend-color" style="background-color:${color};"></div>${name.charAt(0).toUpperCase() + name.slice(1)}: ${weight.toFixed(0)} kg (${percentage.toFixed(1)}%)</div>`;
    }
    pieChart.style.background = gradientString.slice(0, -2) + ')';
}

export function update3DScene(scene, params, weights) {
    if(leftWingMesh){scene.remove(leftWingMesh,rightWingMesh,payloadMesh,motorMesh,propMesh, cmMesh, linesMesh, cpMesh, wingbodyMesh, leftFuelMesh, rightFuelMesh)}
    const sweepDeg = params.sweep;
    const rootProfile=generateNaca4Airfoil('2412',25),tipProfile=generateNaca4Airfoil('0010',25),sweepOffset=params.semiSpan*Math.tan(sweepDeg*Math.PI/180);
    function createWingGeometry(isMirror){const v=[],z=isMirror?-1:1;for(let i=0;i<rootProfile.x.length-1;i++){const r1=new THREE.Vector3(params.wingOffset+rootProfile.x[i]*params.rootChord,rootProfile.y[i]*params.rootChord,(params.payloadWidth/2)*z),r2=new THREE.Vector3(params.wingOffset+rootProfile.x[i+1]*params.rootChord,rootProfile.y[i+1]*params.rootChord,(params.payloadWidth/2)*z),t1=new THREE.Vector3(params.wingOffset+tipProfile.x[i]*params.tipChord+sweepOffset,tipProfile.y[i]*params.tipChord,(params.payloadWidth/2+params.semiSpan)*z),t2=new THREE.Vector3(params.wingOffset+tipProfile.x[i+1]*params.tipChord+sweepOffset,tipProfile.y[i+1]*params.tipChord,(params.payloadWidth/2+params.semiSpan)*z);v.push(r1.x,r1.y,r1.z,r2.x,r2.y,r2.z,t1.x,t1.y,t1.z,t1.x,t1.y,t1.z,r2.x,r2.y,r2.z,t2.x,t2.y,t2.z)}const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(v,3));g.computeVertexNormals();return g}
    const wingMat=new THREE.MeshStandardMaterial({color:0xcccccc,side:THREE.DoubleSide,metalness:0.3,roughness:0.5, transparent: true, opacity: 0.75});
    leftWingMesh=new THREE.Mesh(createWingGeometry(false),wingMat);rightWingMesh=new THREE.Mesh(createWingGeometry(true),wingMat);scene.add(leftWingMesh,rightWingMesh);
    
    const payloadGeom=new THREE.BoxGeometry(params.payloadLength,params.payloadHeight,params.payloadWidth);
    const payloadMat=new THREE.MeshStandardMaterial({color:WEIGHT_COLORS.payload,metalness:0.2,roughness:0.6, transparent: true, opacity: 0.3});
    payloadMesh=new THREE.Mesh(payloadGeom,payloadMat);payloadMesh.position.x=params.payloadLength/2;scene.add(payloadMesh);
    payloadMesh.visible = false;

    const wingbodyRootChord = params.payloadLength;
    const wingbodyTipChord = wingbodyRootChord * 0.85; // 15% taper
    const wingbodySemiSpan = params.payloadWidth / 2;
    const wingbodySweep = 10 * Math.PI / 180;
    const wingbodySweepOffset = wingbodySemiSpan * Math.tan(wingbodySweep);

    function createWingbodyGeometry(isMirror) {
        const v = [], z = isMirror ? -1 : 1;
        const profile = generateNaca4Airfoil('0015', 25);
        const rootHeightScale = params.payloadHeight * 1.1 / 0.15;
        const tipHeightScale = params.payloadHeight / 0.15;

        for (let i = 0; i < profile.x.length - 1; i++) {
            const r1 = new THREE.Vector3(profile.x[i] * wingbodyRootChord, profile.y[i] * rootHeightScale, 0);
            const r2 = new THREE.Vector3(profile.x[i+1] * wingbodyRootChord, profile.y[i+1] * rootHeightScale, 0);
            const t1 = new THREE.Vector3(profile.x[i] * wingbodyTipChord + wingbodySweepOffset, profile.y[i] * tipHeightScale, wingbodySemiSpan * z);
            const t2 = new THREE.Vector3(profile.x[i+1] * wingbodyTipChord + wingbodySweepOffset, profile.y[i+1] * tipHeightScale, wingbodySemiSpan * z);
            v.push(r1.x, r1.y, r1.z, r2.x, r2.y, r2.z, t1.x, t1.y, t1.z, t1.x, t1.y, t1.z, r2.x, r2.y, r2.z, t2.x, t2.y, t2.z);
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
        g.computeVertexNormals();
        return g;
    }
    const wingbodyMat = new THREE.MeshStandardMaterial({color: 0x0000ff, metalness: 0.1, roughness: 0.7, transparent: true, opacity: 0.75, side: THREE.DoubleSide, depthTest: false});
    const leftWingbody = new THREE.Mesh(createWingbodyGeometry(true), wingbodyMat);
    const rightWingbody = new THREE.Mesh(createWingbodyGeometry(false), wingbodyMat);
    wingbodyMesh = new THREE.Group();
    wingbodyMesh.add(leftWingbody, rightWingbody);
    scene.add(wingbodyMesh);

    // --- Fuel Tank Visualization ---
    const fuelDensity = 800; // kg/m^3 for kerosene
    const fuelVolume = weights.fuel / fuelDensity;
    const avgThickness = (params.rootChord * 0.12 + params.tipChord * 0.10) / 2;
    const wingBoxVolume = (params.rootChord + params.tipChord) * params.semiSpan * avgThickness * 0.5; // Approx 50% of wing is fuel tank
    const fuelScale = Math.min(1, Math.cbrt(fuelVolume / (2 * wingBoxVolume)));

    const fuelRootChord = params.rootChord * fuelScale;
    const fuelTipChord = params.tipChord * fuelScale;
    const fuelSemiSpan = params.semiSpan * fuelScale;
    const fuelSweepOffset = fuelSemiSpan * Math.tan(sweepDeg * Math.PI / 180);

    function createFuelTankGeometry(isMirror) {
        const v = [], z = isMirror ? -1 : 1;
        const fuelProfile = generateNaca4Airfoil('0012', 15);
        for (let i = 0; i < fuelProfile.x.length - 1; i++) {
            const r1 = new THREE.Vector3(params.wingOffset + fuelProfile.x[i] * fuelRootChord, fuelProfile.y[i] * fuelRootChord * 0.8, (params.payloadWidth / 2) * z);
            const r2 = new THREE.Vector3(params.wingOffset + fuelProfile.x[i+1] * fuelRootChord, fuelProfile.y[i+1] * fuelRootChord * 0.8, (params.payloadWidth / 2) * z);
            const t1 = new THREE.Vector3(params.wingOffset + fuelProfile.x[i] * fuelTipChord + fuelSweepOffset, fuelProfile.y[i] * fuelTipChord * 0.8, (params.payloadWidth / 2 + fuelSemiSpan) * z);
            const t2 = new THREE.Vector3(params.wingOffset + fuelProfile.x[i+1] * fuelTipChord + fuelSweepOffset, fuelProfile.y[i+1] * fuelTipChord * 0.8, (params.payloadWidth / 2 + fuelSemiSpan) * z);
            v.push(r1.x, r1.y, r1.z, r2.x, r2.y, r2.z, t1.x, t1.y, t1.z, t1.x, t1.y, t1.z, r2.x, r2.y, r2.z, t2.x, t2.y, t2.z);
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
        g.computeVertexNormals();
        return g;
    }
    const fuelMat = new THREE.MeshStandardMaterial({color: WEIGHT_COLORS.fuel, transparent: true, opacity: 0.75});
    leftFuelMesh = new THREE.Mesh(createFuelTankGeometry(false), fuelMat);
    rightFuelMesh = new THREE.Mesh(createFuelTankGeometry(true), fuelMat);
    scene.add(leftFuelMesh, rightFuelMesh);
    const motorGeom=new THREE.BoxGeometry(params.engineSize_m*1.5,params.engineSize_m*1.5,params.engineSize_m*1.5);
    const motorMat=new THREE.MeshStandardMaterial({color:WEIGHT_COLORS.powerplant,metalness:0.8,roughness:0.4});
    motorMesh=new THREE.Mesh(motorGeom,motorMat);motorMesh.position.x=params.payloadLength+params.engineSize_m*1.5/2;scene.add(motorMesh);
    const propGeom=new THREE.CylinderGeometry(params.propellerDiameter_m/2,params.propellerDiameter_m/2,0.02,32);
    const propMat=new THREE.MeshBasicMaterial({color:0x222222,transparent:true,opacity:0.4});
    propMesh=new THREE.Mesh(propGeom,propMat);propMesh.position.x=params.payloadLength+params.engineSize_m*1.5+0.02;propMesh.rotation.z=Math.PI/2;scene.add(propMesh);

    // --- Center of Mass Visualization ---

    const lineMat = new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.5 });
    const lineLength = params.semiSpan * 1.5;
    const points = [
        new THREE.Vector3(-lineLength, 0, 0), new THREE.Vector3(lineLength, 0, 0),
        new THREE.Vector3(0, -lineLength, 0), new THREE.Vector3(0, lineLength, 0),
        new THREE.Vector3(0, 0, -lineLength), new THREE.Vector3(0, 0, lineLength)
    ];
    const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
    linesMesh = new THREE.LineSegments(lineGeom, lineMat);
    linesMesh.position.copy(params.centerOfMass);
    scene.add(linesMesh);

    // --- Center of Pressure Visualization ---
    const cpMat = new THREE.LineBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0.5 });
    const cpLineGeom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, -lineLength, 0), new THREE.Vector3(0, lineLength, 0)]);
    cpMesh = new THREE.Line(cpLineGeom, cpMat);
    cpMesh.position.copy(params.centerOfPressure);
    scene.add(cpMesh);
}

export function updateSliderColors(targetWl, currentWl) {
    // This function may need to be adapted or removed depending on the new UI's logic,
    // as direct wing dimension sliders are replaced by aspect ratio and taper.
    // For now, let's clear the background color of the old sliders.
    const oldSliders = ['semi-span', 'root-chord', 'tip-chord'];
    oldSliders.forEach(id => {
        const label = document.querySelector(`label[for="${id}"]`);
        if (label) {
            label.style.backgroundColor = '';
        }
    });
}
