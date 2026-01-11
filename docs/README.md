# UAV Design Project

## Overview
This project consists of a web-based application for designing and analyzing Unmanned Aerial Vehicles (UAVs). It includes models for both fixed-wing UAVs and multi-copters, allowing users to explore various design parameters and their effects on performance.

## Files
- **quad_test.html**: Models multi-copters with support for a variable number of arms and motors. It features a scale-invariant slider for trade-offs and identifies the trade-offs involved in multi-copter design. Aerodynamic considerations are resolved using existing libraries without modifications.

- **3d_test.html**: Models fixed-wing UAVs, providing a user interface for various parameters such as thrust-to-weight ratio, wing loading, and fuel fraction. It displays performance metrics and includes sliders for user input.

- **js/main.js**: Contains the main logic for both the fixed-wing UAV and multi-copter models. It handles user interactions, updates the UI based on slider values, and performs calculations related to performance metrics and aerodynamic properties.

- **style.css**: Contains the styles for the user interface, ensuring a consistent and visually appealing layout for both `3d_test.html` and `quad_test.html`.

## Usage
1. Open `quad_test.html` or `3d_test.html` in a web browser to access the UAV design interfaces.
2. Adjust the sliders to modify design parameters and observe the changes in performance metrics.
3. Use the information provided in the UI to make informed decisions about UAV design.

## Features
- Interactive sliders for real-time adjustments of design parameters.
- Performance metrics display for both multi-copters and fixed-wing UAVs.
- Aerodynamic analysis using established libraries to ensure accurate results.

## Design and Implementation
The application is built using HTML, CSS, and JavaScript, leveraging modern web technologies to create a responsive and user-friendly interface. The design focuses on usability and clarity, allowing users to easily navigate through the various features and functionalities.