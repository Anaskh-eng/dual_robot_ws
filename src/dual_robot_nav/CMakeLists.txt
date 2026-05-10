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

# ── C++ Executables: Mission Controllers ──────────────────────────────────────
function(add_mission_controller_target target_name source_file output_name)
  add_executable(${target_name}
    ${source_file}
  )

  target_include_directories(${target_name} PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
  )

  ament_target_dependencies(${target_name}
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

  set_target_properties(${target_name} PROPERTIES
    OUTPUT_NAME ${output_name}
  )
endfunction()

add_mission_controller_target(mission_controller src/mission_controller.cpp mission_controller)
add_mission_controller_target(mission_controller_layout2 src/2_mission_controller.cpp 2_mission_controller)
add_mission_controller_target(mission_controller_layout3 src/3_mission_controller.cpp 3_mission_controller)
add_mission_controller_target(mission_controller_layout4 src/4_mission_controller.cpp 4_mission_controller)

# ── Install targets ───────────────────────────────────────────────────────────
install(TARGETS
  mission_controller
  mission_controller_layout2
  mission_controller_layout3
  mission_controller_layout4
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
