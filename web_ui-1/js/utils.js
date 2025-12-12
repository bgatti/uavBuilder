export function formatWeight(weight_kg) {
    if (weight_kg < 1) {
        return `${(weight_kg * 1000).toFixed(0)} g`;
    } else {
        return `${weight_kg.toFixed(2)} kg`;
    }
}

export function formatPower(power_W) {
    if (power_W < 1000) {
        return `${power_W.toFixed(0)} W`;
    } else {
        return `${(power_W / 1000).toFixed(2)} kW`;
    }
}
