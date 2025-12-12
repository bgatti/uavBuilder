import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

def get_prop_performance(V_kts, D_in, P_in, n_rpm, engine_hp_limit, blade_count):
    """
    Final comprehensive model including blade count.
    """
    # --- Constants and Conversions ---
    rho = 1.225
    n_rps = n_rpm / 60.0
    V_mps = V_kts * 0.514444
    D_m = D_in * 0.0254
    P_m = P_in * 0.0254
    speed_of_sound_mps = 343.0

    # --- Blade Count Factors ---
    # These factors model the increase in power absorption and thrust,
    # with diminishing returns for thrust (efficiency loss).
    if blade_count == 2:
        power_factor = 1.0
        thrust_factor = 1.0
    elif blade_count == 3:
        power_factor = 1.25  # Absorbs ~25% more power
        thrust_factor = 1.18 # But produces only ~18% more thrust
    elif blade_count == 4:
        power_factor = 1.45  # Absorbs ~45% more power
        thrust_factor = 1.30 # But produces only ~30% more thrust
    else: # Default to 2-blade
        power_factor = 1.0
        thrust_factor = 1.0

    # --- Aerodynamic Calculations (based on a 2-blade baseline) ---
    J = V_mps / (n_rps * D_m) if (n_rps * D_m) > 0 else 0
    P_D_ratio = P_in / D_in
    
    ct_static = 0.15 * P_D_ratio**0.8
    ct_slope = 0.14
    C_T_base = max(0, ct_static - ct_slope * J)
    
    cp_static = 0.08 * P_D_ratio**1.2
    cp_slope = 0.05
    C_P_base = max(0.01, cp_static - cp_slope * J)
    
    aerodynamic_thrust_N = (C_T_base * rho * n_rps**2 * D_m**4) * thrust_factor
    aerodynamic_power_hp = ((C_P_base * rho * n_rps**3 * D_m**5) / 745.7) * power_factor

    # --- Tip Speed & Compressibility ---
    v_rotational_tip = np.pi * D_m * n_rps
    v_tip_total = np.sqrt(V_mps**2 + v_rotational_tip**2)
    mach_tip = v_tip_total / speed_of_sound_mps
    compress_penalty = 1.0 / (1.0 + np.exp(30 * (mach_tip - 0.95)))
    
    thrust_after_compress = aerodynamic_thrust_N * compress_penalty
    
    # --- Final Performance Calculation ---
    actual_power_hp = min(engine_hp_limit, aerodynamic_power_hp)
    power_ratio = actual_power_hp / aerodynamic_power_hp if aerodynamic_power_hp > 0 else 0
    final_thrust_N = thrust_after_compress * power_ratio
    
    thp = (final_thrust_N * V_mps) / 745.7
    
    return {'thp': thp, 'mach_tip': mach_tip, 'is_power_limited': aerodynamic_power_hp > engine_hp_limit}


#below is test - if __main__:
if __name__ == "__main__":

    # --- Setup for the Matrix Plot ---
    diameters = [27, 28, 29]
    pitches = [18, 19, 20]
    blade_counts = [2, 3, 4]
    colors = ['mediumblue', 'green', 'purple']
    engine_hp = 15
    engine_rpm = 7500

    fig, axes = plt.subplots(nrows=len(diameters), ncols=len(pitches), 
                            figsize=(16, 12), sharex=True, sharey=True)

    for i, D_in in enumerate(diameters):
        for j, P_in in enumerate(pitches):
            ax = axes[i, j]
            
            # Calculate baseline regions for the 2-blade prop
            speeds = np.linspace(1, 160, 150)
            baseline_results = [get_prop_performance(v, D_in, P_in, engine_rpm, engine_hp, 2) for v in speeds]
            is_power_limited = [r['is_power_limited'] for r in baseline_results]
            is_tip_speed_limited = [r['mach_tip'] > 0.85 for r in baseline_results]
            is_aero_limited = [not p and not t for p, t in zip(is_power_limited, is_tip_speed_limited)]
            
            ax.fill_between(speeds, 0, 16, where=is_power_limited, color='skyblue', alpha=0.3)
            ax.fill_between(speeds, 0, 16, where=is_aero_limited, color='lightgreen', alpha=0.3)
            ax.fill_between(speeds, 0, 16, where=is_tip_speed_limited, color='salmon', alpha=0.3)
            
            # Plot curves for each blade count
            for k, b_count in enumerate(blade_counts):
                thp_list = [get_prop_performance(v, D_in, P_in, engine_rpm, engine_hp, b_count)['thp'] for v in speeds]
                ax.plot(speeds, thp_list, color=colors[k], lw=2.5)
            
            # Formatting
            ax.grid(True, which='both', linestyle='--', linewidth='0.5')
            ax.set_ylim(0, 16)
            ax.set_xlim(0, 160)
            
            if j == 0:
                ax.set_ylabel(f'D = {D_in}"', fontsize=14, weight='bold')
            if i == 0:
                ax.set_title(f'Pitch = {P_in}"', fontsize=14, weight='bold')

    # --- Overall Figure Formatting ---
    fig.suptitle('Propeller Performance Envelope Matrix: The Effect of Blade Count (15 HP @ 7500 RPM)', fontsize=20)
    fig.text(0.5, 0.06, 'Airspeed (knots)', ha='center', va='center', fontsize=16)
    fig.text(0.08, 0.5, 'Thrust Horsepower (THP)', ha='center', va='center', rotation='vertical', fontsize=16)

    legend_elements = [Line2D([0], [0], color='mediumblue', lw=2.5, label='2-Blade Prop'),
                    Line2D([0], [0], color='green', lw=2.5, label='3-Blade Prop'),
                    Line2D([0], [0], color='purple', lw=2.5, label='4-Blade Prop'),
                    Patch(facecolor='skyblue', alpha=0.4, label='Power Limited Region'),
                    Patch(facecolor='lightgreen', alpha=0.4, label='Aero Limited Region'),
                    Patch(facecolor='salmon', alpha=0.4, label='Tip Speed Limited Region')]
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.96, 0.96), fontsize=12)

    plt.tight_layout(rect=[0.1, 0.08, 1, 0.95])
    plt.show()
