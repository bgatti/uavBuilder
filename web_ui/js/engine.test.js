import { calculateEngineMetrics } from './engine.js';

function runTests() {
    console.log('Running calculateEngineMetrics tests...');

    // Test Case 1: Light UAV
    let mtow1_kg = 10; // kg
    let thrustToWeightRatio1 = 0.6;
    let metrics1 = calculateEngineMetrics(mtow1_kg, thrustToWeightRatio1);
    console.log('Test Case 1: Light UAV (10kg, 0.6 T/W)');
    console.log(JSON.stringify(metrics1, null, 2));
    console.assert(metrics1.enginePower_kw > 0, 'Test 1 Failed: enginePower_kw should be positive');
    console.assert(metrics1.cruiseSpeed_knots > 0, 'Test 1 Failed: cruiseSpeed_knots should be positive');

    // Test Case 2: Medium UAV
    let mtow2_kg = 50; // kg
    let thrustToWeightRatio2 = 0.5;
    let metrics2 = calculateEngineMetrics(mtow2_kg, thrustToWeightRatio2);
    console.log('\\nTest Case 2: Medium UAV (50kg, 0.5 T/W)');
    console.log(JSON.stringify(metrics2, null, 2));
    console.assert(metrics2.enginePower_kw > metrics1.enginePower_kw, 'Test 2 Failed: enginePower_kw should increase with MTOW');

    // Test Case 3: Heavy UAV
    let mtow3_kg = 150; // kg
    let thrustToWeightRatio3 = 0.4;
    let metrics3 = calculateEngineMetrics(mtow3_kg, thrustToWeightRatio3);
    console.log('\\nTest Case 3: Heavy UAV (150kg, 0.4 T/W)');
    console.log(JSON.stringify(metrics3, null, 2));
    console.assert(metrics3.enginePower_kw > metrics2.enginePower_kw, 'Test 3 Failed: enginePower_kw should increase with MTOW');

    // Test Case 4: High Thrust-to-Weight Ratio
    let mtow4_kg = 25; // kg
    let thrustToWeightRatio4 = 1.2;
    let metrics4 = calculateEngineMetrics(mtow4_kg, thrustToWeightRatio4);
    console.log('\\nTest Case 4: High T/W Ratio (25kg, 1.2 T/W)');
    console.log(JSON.stringify(metrics4, null, 2));
    
    // Test Case 5: Low Thrust-to-Weight Ratio
    let mtow5_kg = 25; // kg
    let thrustToWeightRatio5 = 0.3;
    let metrics5 = calculateEngineMetrics(mtow5_kg, thrustToWeightRatio5);
    console.log('\\nTest Case 5: Low T/W Ratio (25kg, 0.3 T/W)');
    console.log(JSON.stringify(metrics5, null, 2));
    console.assert(metrics4.enginePower_kw > metrics5.enginePower_kw, 'Test 5 Failed: enginePower_kw should be higher for higher T/W ratio');

    console.log('\\nAll tests completed.');
}

runTests();
