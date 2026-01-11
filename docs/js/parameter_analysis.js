let yAxisParam = 'battery-weight-percent';
let xAxisParam = 'payload';

export function getXAxisParam() {
    return xAxisParam;
}

// Function to initialize the parameter analysis feature
export function initParameterAnalysis(drones, updateCallback) {
    const sliders = document.querySelectorAll('.slider-group input[type="range"]');
    const excludedParameters = ['prop-pitch', 'num-motors', 'num-blades'];

    sliders.forEach(slider => {
        slider.addEventListener('mousedown', (event) => {
            const newParam = event.target.id.replace('-slider', '');
            if (xAxisParam !== newParam && !excludedParameters.includes(newParam)) {
                yAxisParam = xAxisParam;
                xAxisParam = newParam;
                updateCallback(xAxisParam);
            }
        });
    });
}

// Function to update the analysis graph
export function updateAnalysisGraph(parameterName, drones, currentUAV) {
    if (!parameterName) {
        parameterName = xAxisParam;
    }
    console.log('Updating analysis graph:', { parameterName, yAxisParam, currentUAV });

    const ctx = document.getElementById('payload-range-graph').getContext('2d');
    const otherUAVs = drones.filter(d => d.name !== currentUAV.name);
    console.log('Other UAVs:', otherUAVs);

    const keyMap = {
        'payload': 'Max_Payload_kg',
        'mtow': 'MTOW_kg',
        'disk-loading': 'Disc_Loading_kg_m2',
        'max-speed': 'Max_Speed_kmh',
        'duration': 'Max_Duration_min',
        'range': 'Max_Range_km',
        'prop-diameter': 'Prop_Dia_in',
        'prop-pitch': 'Prop_Pitch_in',
    };

    const getKey = (obj, key) => {
        if (typeof key !== 'string') {
            console.error('Invalid key provided to getKey:', key);
            return undefined;
        }

        // For the currentUAV object, the key is already correct
        if (obj.name === 'current') {
            return obj[key];
        }

        // For otherUAVs, we need to use the keyMap
        const mappedKey = keyMap[key] || key;
        return obj[mappedKey];
    };

    const allXValues = [...drones.map(d => getKey(d, parameterName)), getKey(currentUAV, parameterName)].filter(v => v !== undefined && !isNaN(v));
    const allYValues = [...drones.map(d => getKey(d, yAxisParam)), getKey(currentUAV, yAxisParam)].filter(v => v !== undefined && !isNaN(v));

    if (allXValues.length === 0 || allYValues.length === 0) {
        console.warn("No data available for the selected parameters to draw the graph.");
        if (window.analysisChart) {
            window.analysisChart.destroy();
        }
        return;
    }

    const xMin = Math.min(...allXValues);
    const xMax = Math.max(...allXValues);
    const yMin = Math.min(...allYValues);
    const yMax = Math.max(...allYValues);

    const xPadding = (xMax - xMin) * 0.1;
    const yPadding = (yMax - yMin) * 0.1;

    const datasets = [
        {
            label: 'Selected UAV',
            data: [{
                x: getKey(currentUAV, parameterName),
                y: getKey(currentUAV, yAxisParam),
                uav: currentUAV
            }],
            backgroundColor: 'rgba(255, 99, 132, 0.8)',
            pointRadius: 8,
        },
        {
            label: 'Other UAVs',
            data: otherUAVs.map(uav => ({
                x: getKey(uav, parameterName),
                y: getKey(uav, yAxisParam),
                uav: uav
            })).filter(d => d.x !== undefined && d.y !== undefined && !isNaN(d.x) && !isNaN(d.y)),
            backgroundColor: 'rgba(54, 162, 235, 0.6)',
            pointRadius: 5,
        }
    ];

    if (window.analysisChart) {
        window.analysisChart.destroy();
    }

    window.analysisChart = new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            animation: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: parameterName.replace(/-/g, ' ').replace(/(?:^|\s)\S/g, a => a.toUpperCase()),
                    },
                    min: xMin - xPadding,
                    max: xMax + xPadding,
                    ticks: {
                        callback: function(value, index, values) {
                            return value.toFixed(2);
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yAxisParam.replace(/-/g, ' ').replace(/(?:^|\s)\S/g, a => a.toUpperCase()),
                    },
                    min: yMin - yPadding,
                    max: yMax + yPadding,
                    ticks: {
                        callback: function(value, index, values) {
                            return value.toFixed(2);
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.dataset.data[context.dataIndex];
                            if (!point || !point.uav) return 'N/A';
                            
                            const uav = point.uav;
                            const xLabel = parameterName.replace(/-/g, ' ').replace(/(?:^|\s)\S/g, a => a.toUpperCase());
                            const yLabel = yAxisParam.replace(/-/g, ' ').replace(/(?:^|\s)\S/g, a => a.toUpperCase());
                            
                            const lines = [uav.Model || uav.name];
                            lines.push(`${xLabel}: ${point.x.toFixed(2)}`);
                            lines.push(`${yLabel}: ${point.y.toFixed(2)}`);
                            return lines;
                        }
                    }
                }
            }
        }
    });
}
