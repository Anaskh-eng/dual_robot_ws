cmake_minimum_required(VERSION 3.8)
project(dual_robot_nav)

# Enforce modern C++ standards
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Find dependencies ──────────────────────────────────────────────────────────
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(std_msgs REQUIRED)

# ── C++ Executable: Mission Controller ────────────────────────────────────────
add_executable(mission_controller
  src/mission_controller.cpp
)

target_include_directories(mission_controller PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(mission_controller
  rclcpp
  rclcpp_action
  geometry_msgs
  nav2_msgs
  nav_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
  ament_index_cpp
  std_msgs
)

# ── Install targets ───────────────────────────────────────────────────────────
install(TARGETS
  mission_controller
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  config
  maps
  worlds
  rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()