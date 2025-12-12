import matplotlib.pyplot as plt
import numpy as np
import gradio as gr

# --- Helper Functions (Unchanged) ---
def triangle_centroid(p1, p2, p3):
    return (p1 + p2 + p3) / 3

def trapezoid_centroid(p1, p2, p3, p4):
    a1 = 0.5 * abs(p1[0]*(p2[1]-p4[1]) + p2[0]*(p4[1]-p1[1]) + p4[0]*(p1[1]-p2[1]))
    c1 = triangle_centroid(p1, p2, p4)
    a2 = 0.5 * abs(p2[0]*(p3[1]-p4[1]) + p3[0]*(p4[1]-p2[1]) + p4[0]*(p2[1]-p3[1]))
    c2 = triangle_centroid(p2, p3, p4)
    if (a1 + a2) == 0: return p1
    total_area = a1 + a2
    centroid_x = (c1[0] * a1 + c2[0] * a2) / total_area
    centroid_y = (c1[1] * a1 + c2[1] * a2) / total_area
    return np.array([centroid_x, centroid_y])

def polygon_area(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- Main Design Function (Refactored for Clarity and Correctness) ---
def create_interactive_uav_plot(
    payload_length, payload_width, payload_weight, wing_semi_span, aspect_ratio,
    motor_payload_weight_ratio, fuel_fraction, motor_length
):
    """
    Designs a UAV and returns the Matplotlib figure.
    This version includes the UI button logic, corrected rotation, and clearer naming.
    """
    # --- Constants ---
    wing_surface_density, fuselage_surface_density = 3.0, 4.0
    nose_length_factor, tail_length_factor = 0.3, 0.2

    # --- Iterative Solver ---
    sweep_deg = 30.0
    for _ in range(30): # Use _ as 'i' is not needed
        sweep_rad = np.radians(sweep_deg)
        taper_ratio = max(0.05, 1 / aspect_ratio)
        root_chord = payload_length
        tip_chord = root_chord * taper_ratio
        
        # --- 1. Define Explicit, Named Vertices (Original Orientation) ---
        nose_length = payload_length * nose_length_factor
        tail_length = payload_length * tail_length_factor
        motor_start_x = payload_length
        
        # Define fuselage and root points
        nose_tip = np.array([-nose_length, 0])
        tail_tip = np.array([motor_start_x + motor_length + tail_length, 0])
        right_wing_root_le = np.array([0, payload_width / 2.0])
        right_wing_root_te = np.array([payload_length, payload_width / 2.0])
        left_wing_root_le = np.array([0, -payload_width / 2.0])
        left_wing_root_te = np.array([payload_length, -payload_width / 2.0])

        # Calculate wing tip positions based on sweep
        tip_le_x = right_wing_root_le[0] + wing_semi_span * np.tan(sweep_rad)
        tip_y = wing_semi_span
        
        right_wing_tip_le = np.array([tip_le_x, right_wing_root_le[1] + tip_y])
        right_wing_tip_te = np.array([tip_le_x + tip_chord, right_wing_root_le[1] + tip_y])
        left_wing_tip_le = np.array([tip_le_x, left_wing_root_le[1] - tip_y])
        left_wing_tip_te = np.array([tip_le_x + tip_chord, left_wing_root_le[1] - tip_y])

        # --- 2. Calculate Weights and CG (Same as before) ---
        weights, centroids = [], []
        # Payload, Motor
        weights.append(payload_weight); centroids.append(np.array([payload_length/2, 0]))
        weights.append(payload_weight*motor_payload_weight_ratio); centroids.append(np.array([motor_start_x + motor_length/2, 0]))
        # Wings
        right_wing_verts = [right_wing_root_le, right_wing_root_te, right_wing_tip_te, right_wing_tip_le]
        wing_area = polygon_area(*zip(*right_wing_verts))
        weights.append(2*wing_area*wing_surface_density); centroids.append(np.array([trapezoid_centroid(*right_wing_verts)[0], 0]))
        # Fuselage
        nose_area = polygon_area(*zip(*[nose_tip, right_wing_root_le, left_wing_root_le]))
        center_body_area = payload_length * payload_width
        tail_area = polygon_area(*zip(*[right_wing_root_te, tail_tip, left_wing_root_te]))
        weights.append((nose_area+center_body_area+tail_area)*fuselage_surface_density); centroids.append(np.array([(payload_length+motor_length)/2, 0]))
        # Fuel
        w_dry = sum(weights)
        w_gtow = w_dry / (1 - fuel_fraction)
        w_fuel = w_gtow - w_dry
        weights.append(w_fuel); centroids.append(np.array([payload_length/2, 0]))
        
        # Calculate final CG and required sweep
        total_weight = sum(weights)
        cg_x = sum(w * c[0] for w, c in zip(weights, centroids)) / total_weight
        required_sweep_rad = np.arctan(cg_x / wing_semi_span)
        required_sweep_deg = np.degrees(required_sweep_rad)
        
        if abs(required_sweep_deg - sweep_deg) < 0.01: break
        sweep_deg = 0.6 * sweep_deg + 0.4 * required_sweep_deg

    # --- 3. Plotting with Corrected Rotation ---
    fig, ax = plt.subplots(figsize=(10, 12))

    # Assemble the final outline from named vertices
    outline_vertices = [
        nose_tip, left_wing_tip_le, left_wing_tip_te, left_wing_root_te, tail_tip,
        right_wing_root_te, right_wing_tip_te, right_wing_tip_le, nose_tip
    ]
    x_coords, y_coords = zip(*outline_vertices)
    
    # ROTATE: Plot -y vs x
    ax.plot([-y for y in y_coords], x_coords, 'r-o', label='UAV Airframe', zorder=10)

    # 3b. Correctly define rotated rectangles
    # For a 90-deg rotation, the new (x,y) is (-y_orig, x_orig). Width and height are swapped.
    payload_rotated_anchor = (-left_wing_root_le[1], left_wing_root_le[0])
    payload_rect = plt.Rectangle(payload_rotated_anchor, payload_width, payload_length, ec='blue', fc='lightblue', ls='--', label='Payload Bay', zorder=5)
    ax.add_patch(payload_rect)
    
    motor_rotated_anchor = (-left_wing_root_te[1], left_wing_root_te[0])
    motor_rect = plt.Rectangle(motor_rotated_anchor, payload_width, motor_length, ec='black', fc='gray', ls='--', label='Motor', zorder=5)
    ax.add_patch(motor_rect)
    
    # Plot CG and alignment line (rotated)
    ax.plot(0, cg_x, 'kx', markersize=15, markeredgewidth=3, label='Aircraft CG', zorder=20)
    ax.axhline(y=cg_x, color='k', linestyle=':', label='CG / Tip LE Alignment')

    # Formatting
    ax.set_title(f"Calculated Sweep: {sweep_deg:.2f}° | GTOW: {total_weight:.1f}kg")
    ax.set_xlabel('Width (m)'); ax.set_ylabel('Length (m)')
    ax.grid(True); ax.set_aspect('equal', adjustable='box'); ax.legend()
    
    plt.close(fig) # Prevent duplicate display
    return fig

# --- 4. Build the Gradio UI with a "Generate" Button ---
with gr.Blocks(theme=gr.themes.Soft()) as iface:
    gr.Markdown("# Interactive UAV Designer (v2)")
    gr.Markdown("Adjust the sliders below, then click **Generate Design** to see the result. This prevents lag from continuous updates.")
    with gr.Row():
        with gr.Column(scale=1):
            # Input Sliders
            payload_length_slider = gr.Slider(1.0, 10.0, value=4.0, step=0.5, label="Payload Length (m)")
            payload_width_slider = gr.Slider(0.3, 3.0, value=0.8, step=0.1, label="Payload Width (m)")
            payload_weight_slider = gr.Slider(20, 500, value=150, step=10, label="Payload Weight (kg)")
            wing_semi_span_slider = gr.Slider(3.0, 15.0, value=6.0, step=0.5, label="Wing Semi-Span (m)")
            aspect_ratio_slider = gr.Slider(2.0, 12.0, value=3.0, step=0.5, label="Aspect Ratio")
            motor_ratio_slider = gr.Slider(0.1, 2.0, value=0.4, step=0.1, label="Motor/Payload Weight Ratio")
            fuel_fraction_slider = gr.Slider(0.1, 0.6, value=0.35, step=0.05, label="Fuel Fraction of GTOW")
            motor_length_slider = gr.Slider(0.5, 3.0, value=1.0, step=0.1, label="Motor Length (m)")
            
            # The Generate Button
            btn = gr.Button("Generate Design", variant="primary")
        
        with gr.Column(scale=2):
            plot_output = gr.Plot()

    # Define the list of inputs for the function
    inputs = [
        payload_length_slider, payload_width_slider, payload_weight_slider, wing_semi_span_slider,
        aspect_ratio_slider, motor_ratio_slider, fuel_fraction_slider, motor_length_slider
    ]
    
    # The button click is now the trigger
    btn.click(fn=create_interactive_uav_plot, inputs=inputs, outputs=plot_output)
    
    # Load a default plot on startup
    iface.load(fn=create_interactive_uav_plot, inputs=inputs, outputs=plot_output)

# Launch the app
iface.launch()
