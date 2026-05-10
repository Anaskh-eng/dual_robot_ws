# Dual Robot Warehouse Navigation (ROS 2 Humble)

![ROS 2](https://img.shields.io/badge/ROS2-Humble-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Nav2](https://img.shields.io/badge/Navigation-Nav2-orange)

A professional ROS 2 workspace demonstrating multi-robot coordination and navigation in a shared warehouse environment. This project features two TurtleBot3 (Waffle Pi) robots operating concurrently using the ROS 2 Navigation Stack (Nav2) and CycloneDDS for robust communication.

---

## 🌟 Overview

This project simulates a realistic warehouse automation scenario where two mobile robots coordinate to perform "Pick and Place" style movement tasks. It provides a complete pipeline from world simulation in Gazebo to high-level mission orchestration via a custom C++ controller.

### Key Features
- **Multi-Robot Navigation:** Independent Nav2 stacks for `TB3_1` and `TB3_2` operating in the same map.
- **Shared Warehouse Environment:** Custom Gazebo worlds designed for industrial automation workflows.
- **Robust Communication:** Optimized for **CycloneDDS** to ensure low-latency and reliable message passing between namespaces.
- **Mission Orchestration:** A centralized C++ Mission Controller that manages task dispatching and robot state monitoring.
- **Modular Layouts:** Support for multiple warehouse configurations and mission sets (Layouts 1-4).

---

## 🚀 Quick Start

### 1. Prerequisites
- **OS:** Ubuntu 22.04
- **ROS 2:** Humble Hawksbill
- **Simulation:** Gazebo (Classic)
- **Dependencies:**
  ```bash
  sudo apt update
  sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup \
                   ros-humble-turtlebot3-gazebo ros-humble-turtlebot3-description \
                   ros-humble-rmw-cyclonedds-cpp
  ```

### 2. Installation & Build
```bash
# Clone the repository
git clone https://github.com/Anaskh-eng/dual_robot_ws.git
cd dual_robot_ws

# Build the workspace
colcon build --symlink-install
```

### 3. Launching the Simulation
We provide a comprehensive environment setup script to handle DDS configuration and ROS variables.

**Terminal 1: Full Bringup**
```bash
source setup_env.sh
ros2 launch dual_robot_nav 00_bringup.launch.py
```
*Note: This command orchestrates the Gazebo world, robot spawning, Nav2 stacks, and the Mission Controller in sequence.*

---

## 🏗 Project Architecture

### Directory Structure
```text
dual_robot_ws/
├── src/
│   └── dual_robot_nav/
│       ├── config/        # Nav2 parameters and CycloneDDS XML
│       ├── launch/        # Orchestrated launch files (Stages 00-33)
│       ├── maps/          # Static maps (.yaml & .pgm) for warehouse layouts
│       ├── src/           # Mission Controller C++ source code
│       └── worlds/        # Gazebo .world files
├── setup_env.sh           # Environment & RMW configuration script
└── check_setup.sh         # Dependency validation script
```

### Communication Strategy (CycloneDDS)
To prevent cross-talk and ensure performance in a multi-robot setup, we use CycloneDDS with a custom configuration. The `cyclonedds.xml` file optimizes the internal ROS 2 middleware for the dual-namespace environment.

### Mission Control Logic
The `mission_controller` node (C++) acts as the brain of the operation:
1. **Initializes** Action Clients for both robots.
2. **Monitors** the status of Nav2 servers.
3. **Dispatches** concurrent goals (e.g., `Loading Dock` -> `Machine M1`).
4. **Handles** task completion callbacks to chain subsequent movements.

---

## 🛠 Advanced Usage

### Switching Layouts
The project supports different warehouse configurations. To launch a specific layout (e.g., Layout 2):
```bash
ros2 launch dual_robot_nav 10_bringup.launch.py  # Layout 2 orchestration
```

### Running Components Individually
If you need more control during debugging, you can run the phases manually (ensure `setup_env.sh` is sourced):
1. **World:** `ros2 launch dual_robot_nav 01_gazebo_world.launch.py`
2. **Spawn:** `ros2 launch dual_robot_nav 02_spawn_robots.launch.py`
3. **Nav:** `ros2 launch dual_robot_nav 03_navigation.launch.py`

---

## 🤝 Contributing
Contributions are welcome! If you find a bug or have a feature request, please open an issue or submit a pull request.

---

## 📄 License
This project is licensed under the **Apache-2.0 License** - see the `LICENSE` file (if available) or `package.xml` for details.

---
*Developed by Anas KH*
