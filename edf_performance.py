import numpy as np
import matplotlib.pyplot as plt
import os
import math

# ==============================================================================
# 1. IMPORT AIRCRAFT CONFIGURATIONS
# ==============================================================================
try:
    from edf_config import generate_aircraft_scenarios, Aircraft, EDF
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import from 'edf_config.py'.")
    print(f"Please ensure all required .py files are in the same directory.")
    print(f"Original Error: {e}")
    exit()

# ==============================================================================
# 2. AVIATION FORMULAS AND ANALYSIS
# ==============================================================================
G = 9.80665; RHO_SL_KGM3 = 1.225

def get_air_density(altitude_ft):
    altitude_m = altitude_ft * 0.3048; temp_c = 15.04 - 0.00649 * altitude_m
    pressure_pa = 101325 * (1 - 0.0065 * altitude_m / 288.15)**5.2561
    return pressure_pa / (287.05 * (temp_c + 273.15))

def analyze_cruise_performance_vs_altitude(aircraft: Aircraft):
    """Analyzes performance at the designated cruise IAS across various altitudes."""
    altitudes_ft = np.linspace(0, 45000, 100)
    weight_n = aircraft.mtow_kg * G; thrust_required_n = weight_n / aircraft.ld_ratio
    results = {'alt_ft': altitudes_ft, 'range_km': [], 'endurance_hr': []}
    for alt in altitudes_ft:
        rho_alt = get_air_density(alt)
        tas_mps = aircraft.cruise_ias_mps / math.sqrt(rho_alt / RHO_SL_KGM3)
        power_required_w = (thrust_required_n * tas_mps) / aircraft.edf.propulsive_efficiency
        if power_required_w > 0:
            endurance_s = aircraft.battery.total_energy_j / power_required_w
            results['endurance_hr'].append(endurance_s / 3600)
            results['range_km'].append((tas_mps * endurance_s) / 1000)
        else:
            results['endurance_hr'].append(0); results['range_km'].append(0)
    return results

def analyze_roc_vs_tas(aircraft: Aircraft, altitude_ft: float):
    """Analyzes Rate of Climb across a range of airspeeds at a specific altitude."""
    rho_alt = get_air_density(altitude_ft); weight_n = aircraft.mtow_kg * G
    # Analyze from stall speed up to a high speed
    v_stall_ias = math.sqrt((2 * weight_n) / (rho_alt * aircraft.wing_area_m2 * 1.5))
    tas_mps_range = np.linspace(v_stall_ias / math.sqrt(rho_alt/RHO_SL_KGM3), 200, 100)
    
    roc_fpm_list = []
    for tas_mps in tas_mps_range:
        thrust_avail = aircraft.edf.get_thrust(altitude_ft, tas_mps)
        # For a parabolic drag polar, Thrust_req = Drag. Assume constant L/D for simplicity.
        thrust_req = weight_n / aircraft.ld_ratio
        excess_thrust = thrust_avail - thrust_req
        roc_mps = (excess_thrust / weight_n) * tas_mps if excess_thrust > 0 else 0
        roc_fpm_list.append(roc_mps * 196.85)
        
    return tas_mps_range * 1.94384, roc_fpm_list

# ==============================================================================
# 3. NEW PLOTTING FUNCTIONS
# ==============================================================================

def plot_climb_envelopes(ax, all_results):
    """Plots Rate of Climb vs. True Airspeed for different altitudes."""
    altitudes_to_plot = [0, 10000, 20000]
    line_styles = ['-', '--', ':']
    for res in all_results:
        for i, alt in enumerate(altitudes_to_plot):
            tas_kts, roc_fpm = analyze_roc_vs_tas(res['aircraft'], alt)
            ax.plot(tas_kts, roc_fpm, color=res['color'], linestyle=line_styles[i],
                    label=f"{res['name']} @ {alt/1000:.0f}k ft" if i==0 else None)
    # Create custom legend for line styles
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color='gray', lw=2, linestyle=ls, label=f'{alt/1000:.0f}k ft Alt') for alt, ls in zip(altitudes_to_plot, line_styles)]
    ax.legend(handles=legend_elements, title="Altitude", loc='upper right')
    ax.set_title("Climb Performance Envelope", fontsize=16)
    ax.set_xlabel("True Airspeed (knots)", fontsize=12)
    ax.set_ylabel("Rate of Climb (ft/min)", fontsize=12)
    ax.grid(True, linestyle='--')

def plot_range_endurance_profiles(ax, all_results):
    """Plots Range and Endurance vs. Altitude."""
    ax.set_title("Range & Endurance Profiles", fontsize=16)
    ax.set_xlabel("Max Range (km)", fontsize=12)
    ax.set_ylabel("Altitude (ft)", fontsize=12)
    ax_twin = ax.twiny()
    ax_twin.set_xlabel("Max Endurance (hours)", fontsize=12)

    for res in all_results:
        cruise_perf = analyze_cruise_performance_vs_altitude(res['aircraft'])
        ls = '--' if 'Endurance' in res['name'] else '-'
        # Plot Range on the primary axis
        ax.plot(cruise_perf['range_km'], cruise_perf['alt_ft'], color=res['color'], linestyle=ls, label=res['name'])
        # Plot Endurance on the secondary axis
        ax_twin.plot(cruise_perf['endurance_hr'], cruise_perf['alt_ft'], color=res['color'], linestyle=':', alpha=0.7)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=3, fontsize=9)
    ax.grid(True, linestyle='--')

def plot_kpi_radar_chart(ax, all_results):
    """Plots a multi-metric radar chart to compare designs."""
    kpis = ['Cruise IAS', 'Max Range', 'Max RoC', 'L/D Ratio', 'MTOW']
    num_vars = len(kpis)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1] # complete the loop

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), kpis)

    # Normalize data for plotting
    all_data = []
    for res in all_results:
        tas, roc = analyze_roc_vs_tas(res['aircraft'], 0) # Get Sea Level performance
        data = [
            res['aircraft'].cruise_ias_kts,
            max(analyze_cruise_performance_vs_altitude(res['aircraft'])['range_km']),
            max(roc),
            res['aircraft'].ld_ratio,
            res['aircraft'].mtow_kg
        ]
        all_data.append(data)
    
    all_data = np.array(all_data)
    # Invert MTOW so smaller is "better" on the plot
    all_data[:, 4] = max(all_data[:, 4]) - all_data[:, 4]
    normalized_data = all_data / all_data.max(axis=0)

    for i, res in enumerate(all_results):
        data = normalized_data[i].tolist()
        data += data[:1] # complete the loop
        ls = '--' if 'Endurance' in res['name'] else '-'
        ax.plot(angles, data, color=res['color'], linewidth=2, linestyle=ls, label=res['name'])
    
    ax.set_title("Key Performance Indicator Summary", fontsize=16, y=1.1)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=3, fontsize=9)

# ==============================================================================
# 4. MAIN EXECUTION BLOCK
# ==============================================================================
if __name__ == "__main__":
    os.makedirs('processed_uav_data', exist_ok=True)
    print("--- Aircraft Performance Analyzer v2 ---")
    
    configured_aircraft = generate_aircraft_scenarios()
    if not configured_aircraft: print("\nNo aircraft configurations were generated."); exit()

    all_results = []
    cmap = plt.cm.viridis(np.linspace(0, 1, len(configured_aircraft)))
    for i, aircraft in enumerate(configured_aircraft):
        name = f"{aircraft.edf.name.split(' ')[0]} {'Endurance' if aircraft.params.endurance.percent > 50 else 'Sprint'}"
        all_results.append({'aircraft': aircraft, 'name': name, 'color': cmap[i]})
        
    # --- Create the combined plot ---
    fig = plt.figure(figsize=(28, 8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8])
    
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2], polar=True) # Use polar projection for radar chart
    
    plot_climb_envelopes(ax1, all_results)
    plot_range_endurance_profiles(ax2, all_results)
    plot_kpi_radar_chart(ax3, all_results)
    
    fig.suptitle("Comprehensive Aircraft Performance Analysis", fontsize=22)
    plt.tight_layout(rect=[0, 0.05, 1, 0.95]) # Adjust for legends
    
    save_path = "processed_uav_data/new_comprehensive_analysis.png"; plt.savefig(save_path)
    print(f"\nAnalysis plots saved to '{save_path}'")
    plt.show()