import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.animation import FuncAnimation
from uav_parameters import FixedWingParameters
from edf_config import Aircraft, EDF
from lipo import Battery

def create_cylinder(radius, height, position, resolution=50):
    """Creates coordinates for a cylinder centered at a given position."""
    x = np.linspace(position[0] - height / 2, position[0] + height / 2, resolution)
    theta = np.linspace(0, 2 * np.pi, resolution)
    x_grid, theta_grid = np.meshgrid(x, theta)
    y_grid = radius * np.cos(theta_grid) + position[1]
    z_grid = radius * np.sin(theta_grid) + position[2]
    return x_grid, y_grid, z_grid

def display_uav_3d(aircraft: Aircraft):
    """
    Generates and displays a 3D model of a simple EDF UAV with auto-rotation.
    """
    # 1. Extract Parameters and Apply New Rules
    wingspan = aircraft.params.wingspan.value
    edf_diameter = aircraft.edf.diameter_m
    
    # --- Geometric Scaling based on EDF and new rules ---
    body_radius = edf_diameter / 2
    body_length = edf_diameter * 8  # Body aspect ratio is 8:1
    
    wing_area = aircraft.wing_area_m2
    aspect_ratio = wingspan**2 / wing_area
    wing_chord = wingspan / aspect_ratio

    # Tail dimensions
    tail_span = wingspan * 0.4
    tail_chord = wing_chord * 0.6
    # Position tail at the end of the fuselage
    tail_center_pos_x = -body_length / 2 + tail_chord / 2

    # 2. Generate 3D Coordinates
    
    # --- Fuselage ---
    fuselage_x, fuselage_y, fuselage_z = create_cylinder(body_radius, body_length, (0, 0, 0))

    # --- EDF Unit (Equilateral and Red) ---
    edf_length = edf_diameter  # Equilateral cylinder
    edf_pos_x = -body_length / 2 - edf_length / 2 # Place it just behind the fuselage
    edf_x, edf_y, edf_z = create_cylinder(body_radius, edf_length, (edf_pos_x, 0, 0))

    # --- Main Wing (Tapered, Swept, and Separated by Fuselage) ---
    tip_chord = wing_chord * 0.6
    root_chord = wing_chord * 1.4
    sweep_angle_deg = 20
    sweep_offset = (wingspan/2 - body_radius) * np.tan(np.deg2rad(sweep_angle_deg))

    # Right wing panel
    x_le_root = root_chord / 2
    x_te_root = -root_chord / 2
    x_le_tip = x_le_root - sweep_offset
    x_te_tip = x_le_tip - tip_chord
    
    x_coords_r = np.array([x_le_root, x_te_root, x_te_tip, x_le_tip, x_le_root])
    y_coords_r = np.array([body_radius, body_radius, wingspan/2, wingspan/2, body_radius])
    verts_right = [list(zip(x_coords_r, y_coords_r, np.zeros_like(x_coords_r)))]

    # Left wing panel
    x_coords_l = np.array([x_le_root, x_te_root, x_te_tip, x_le_tip, x_le_root])
    y_coords_l = -np.array([body_radius, body_radius, wingspan/2, wingspan/2, body_radius])
    verts_left = [list(zip(x_coords_l, y_coords_l, np.zeros_like(x_coords_l)))]

    # --- Tail Surfaces ---
    tail_tip_chord = tail_chord * 0.7
    tail_x = np.array([-tail_chord/2, tail_chord/2, tail_tip_chord/2, -tail_tip_chord/2, -tail_chord/2]) + tail_center_pos_x
    tail_y = np.array([-tail_span/2, -tail_span/2, tail_span/2, tail_span/2, -tail_span/2])
    v_stab_x = np.array([-tail_chord/2, tail_chord/2, tail_chord*0.8, -tail_chord/2]) + tail_center_pos_x
    v_stab_z = np.array([0, 0, tail_span * 0.5, 0])

    # 3. Plotting
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')

    # Plot Fuselage and EDF
    ax.plot_surface(fuselage_x, fuselage_y, fuselage_z, color='silver', alpha=0.6, rstride=1, cstride=1)
    ax.plot_surface(edf_x, edf_y, edf_z, color='red', alpha=0.8, rstride=1, cstride=1)

    # Plot Wings and Tail
    ax.add_collection3d(Poly3DCollection(verts_right, facecolors='cyan', linewidths=1, edgecolors='k', alpha=0.9))
    ax.add_collection3d(Poly3DCollection(verts_left, facecolors='cyan', linewidths=1, edgecolors='k', alpha=0.9))
    ax.plot(tail_x, tail_y, np.zeros_like(tail_x), color='magenta', lw=3)
    ax.plot(v_stab_x, np.zeros_like(v_stab_x), v_stab_z, color='magenta', lw=3)

    # --- Set plot limits and labels for equal aspect ratio ---
    max_range = max(body_length, wingspan) * 0.75
    ax.set_xlim(-max_range, max_range)
    ax.set_ylim(-max_range, max_range)
    ax.set_zlim(-max_range, max_range)
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
    ax.set_title(f"3D View: {aircraft.params.name}")
    ax.set_box_aspect([1,1,1]) # Enforce equal aspect ratio

    # 4. Auto-rotation Animation
    def update_view(frame):
        ax.view_init(elev=30, azim=frame)
        return fig,

    # Disable blit to fix the TypeError
    ani = FuncAnimation(fig, update_view, frames=np.arange(0, 360, 2), blit=False, interval=50)
    plt.show()

if __name__ == "__main__":
    # --- Configuration for a Sprint UAV ---
    sprint_params = FixedWingParameters()
    sprint_params.name = "Sprint UAV"
    sprint_params.endurance.percent = 10
    sprint_params.cruise_speed.percent = 90
    sprint_params.wingspan.percent = 40

    # --- Configuration for an Endurance UAV ---
    endurance_params = FixedWingParameters()
    endurance_params.name = "Endurance UAV"
    endurance_params.endurance.percent = 90
    endurance_params.cruise_speed.percent = 30
    endurance_params.wingspan.percent = 80

    # --- Create Battery and EDF ---
    battery = Battery.from_c_and_weight(c_rating=30, max_weight_kg=5.0)
    edf = EDF.from_power(power_w=8000)

    # --- Create Aircraft Instances ---
    sprint_uav = Aircraft(edf, battery, sprint_params)
    endurance_uav = Aircraft(edf, battery, endurance_params)

    print("--- Sprint UAV ---")
    for line in sprint_uav.get_summary(): print(line)
    display_uav_3d(sprint_uav)

    print("\n--- Endurance UAV ---")
    for line in endurance_uav.get_summary(): print(line)
    display_uav_3d(endurance_uav)
