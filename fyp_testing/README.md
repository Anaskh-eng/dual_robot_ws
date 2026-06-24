# FYP Navigation Testing Framework

This folder contains thesis testing tools for the existing ROS 2/Nav2 FMS project.
It does not replace or rewrite the working launch files.

## Project Summary

`~/dual_robot_ws` contains the dual-robot Nav2 system:

- Package: `dual_robot_nav`
- Robots: `/TB3_1` and `/TB3_2`
- Layout launches:
  - Layout 1: `ros2 launch dual_robot_nav 00_bringup.launch.py`
  - Layout 2: `ros2 launch dual_robot_nav 10_bringup.launch.py`
  - Layout 3: `ros2 launch dual_robot_nav 20_bringup.launch.py`
  - Layout 4: `ros2 launch dual_robot_nav 30_bringup.launch.py`
- Nav2 params:
  - `nav2_params_tb3_1.yaml`
  - `nav2_params_tb3_2.yaml`
- Maps/worlds:
  - `fms_layout1` to `fms_layout4`

`~/Anasros2_ws` contains the single-robot comparison stack:

- Packages: `single_robot_nav`, `mission_planner`
- Missions:
  - `single_robot_nav`
  - `single_robot_nav_fms2`
  - `single_robot_nav_fms3`
  - `single_robot_nav_fms4`
- Nav2 params: `single_robot_nav/config/nav2_params.yaml`

## Results Structure

```text
fyp_testing/
  results/
    bags/      # rosbag2 recordings
    csv/       # metrics and thesis tables
    plots/     # reserved for generated plots
    logs/      # launch, mission, and rosbag logs
    params/    # generated temporary inflation-radius params
```

## Recorded Topics

Dual-robot runs record:

```text
/clock
/rosout
/gazebo/model_states
/TB3_1/odom
/TB3_2/odom
/TB3_1/amcl_pose
/TB3_2/amcl_pose
/TB3_1/plan
/TB3_2/plan
/TB3_1/cmd_vel
/TB3_2/cmd_vel
/TB3_1/scan
/TB3_2/scan
```

Single-robot runs record:

```text
/clock
/rosout
/gazebo/model_states
/odom
/amcl_pose
/plan
/cmd_vel
/scan
```

## Run A Dual-Robot Experiment

From any terminal:

```bash
cd ~/dual_robot_ws/fyp_testing
./scripts/run_dual_experiment.sh 1 1 420
```

Arguments:

```text
./scripts/run_dual_experiment.sh <layout> <repeat> <duration_sec> [inflation_radius_label] [visual|headless]
```

Examples:

```bash
./scripts/run_dual_experiment.sh 1 1 420
./scripts/run_dual_experiment.sh 2 3 420
./scripts/run_dual_experiment.sh 4 5 480
```

To watch the robots in Gazebo and RViz:

```bash
./scripts/run_dual_experiment.sh 1 1 420 default visual
```

## Run A Single-Robot Experiment

```bash
cd ~/dual_robot_ws/fyp_testing
./scripts/run_single_experiment.sh 1 1 420
```

The single-robot mission is configured to start from the same front-of-L/U
pose used by the dual layout's `TB3_1` robot. The waypoint order is:

```text
L/U -> M1 -> M2 -> L/U -> M3 -> M4 -> L/U
```

Arguments:

```text
./scripts/run_single_experiment.sh <layout> <repeat> <duration_sec> [inflation_radius_label] [visual|headless]
```

Examples:

```bash
./scripts/run_single_experiment.sh 1 1 420
./scripts/run_single_experiment.sh 2 3 420
./scripts/run_single_experiment.sh 4 5 480
```

To open RViz while the single-robot mission runs:

```bash
./scripts/run_single_experiment.sh 1 1 420 default visual
```

## Repeat Runs

For five repeats of dual-robot layout 1:

```bash
for r in 1 2 3 4 5; do
  ./scripts/run_dual_experiment.sh 1 "$r" 420
done
```

For five repeats of single-robot layout 1:

```bash
for r in 1 2 3 4 5; do
  ./scripts/run_single_experiment.sh 1 "$r" 420
done
```

## Inflation Radius Sweep

The sweep tests:

```text
0.55, 0.40, 0.30, 0.25, 0.20
```

Dual-robot layout 1, five repeats:

```bash
./scripts/run_inflation_sweep.sh dual 1 5 420
```

Gazebo smoke test, one repeat per radius:

```bash
./scripts/run_inflation_sweep.sh dual 1 1 180 gui
```

Test one radius only:

```bash
FYP_RADII="0.40" ./scripts/run_inflation_sweep.sh dual 1 1 180 gui
```

Gazebo plus RViz smoke test:

```bash
./scripts/run_inflation_sweep.sh dual 1 1 180 visual
```

Single-robot layout 1, five repeats:

```bash
./scripts/run_inflation_sweep.sh single 1 5 420
```

The fifth argument can be `headless`, `gui`, `rviz`, or `visual`. Use `gui` for
Gazebo only, and `visual` for Gazebo plus RViz. Dual runs stop early after both
robots finish and return to the loading dock, so the duration is now a maximum
timeout rather than the expected runtime.

The scripts generate temporary parameter files or overlays under:

```text
results/params/
```

Original Nav2 YAML files are not edited.

## Namespace Isolation Check

Start a dual-robot simulation first, then run:

```bash
cd ~/dual_robot_ws/fyp_testing
./scripts/namespace_check.sh | tee results/logs/namespace_check_layout1.txt
```

Check the output for:

- `/TB3_1/cmd_vel` and `/TB3_2/cmd_vel` both present
- separate publishers/subscribers for each namespaced topic
- reasonable frequencies for `/scan`, `/odom`, and `/cmd_vel`

## TF Frame / Namespace Graph Capture

Start a dual-robot simulation first, then capture TF frame graph PDFs and a
topic isolation text snapshot:

```bash
cd ~/dual_robot_ws/fyp_testing
./scripts/capture_dual_frames.sh dual_namespaces
```

This creates files under:

```text
results/plots/
```

The script creates one global check plus separate `TB3_1` and `TB3_2` frame
PDFs, because the project intentionally publishes TF on `/TB3_1/tf` and
`/TB3_2/tf` rather than a shared global `/tf`. The robot-specific PDFs are useful
as visual evidence that the robots have separated TF trees. The text file
supports the figure by showing namespaced nodes, topics, publishers, and
subscribers.

## DDS / Fault Isolation Test

This test demonstrates ROS2 DDS fault isolation: one robot's Nav2 nodes can fail
without shutting down the other robot's namespace, topics, and navigation stack.

Kill `TB3_1` Nav2 nodes during a layout 1 mission:

```bash
./scripts/run_fault_isolation_test.sh 1 1 240 TB3_1 nav2 95 gui
```

Arguments:

```text
<layout> <repeat> <duration_sec> <target_robot> <fault_type> <fault_delay_sec> <visual_mode>
```

Fault types:

```text
nav2          kills bt_navigator, controller_server, planner_server
controller    kills controller_server only
localization  kills amcl and map_server
```

Useful examples:

```bash
./scripts/run_fault_isolation_test.sh 1 1 240 TB3_1 nav2 95 gui
./scripts/run_fault_isolation_test.sh 1 2 240 TB3_2 controller 95 gui
./scripts/run_fault_isolation_test.sh 2 1 240 TB3_1 localization 95 headless
```

The script writes:

```text
results/csv/<run_id>_metrics.csv
results/csv/<run_id>_fault_isolation.csv
results/csv/<run_id>_fault_events.csv
results/logs/<run_id>/fault_injection.log
results/logs/<run_id>/<run_id>_post_fault_topic_isolation.txt
results/logs/<run_id>/<run_id>_post_fault_frames.pdf
```

Thesis interpretation:

- `survivor_continued=true` supports the claim that the surviving robot's DDS
  communication graph and Nav2 stack continued after the other robot's fault.
- `survivor_finished=true` in the fault events CSV means the surviving robot
  returned to the loading dock, so the script stopped the simulation cleanly.
- The post-fault frame PDF can be used as visual evidence that the surviving
  robot's TF frame tree and namespaced graph were still available.
- The post-fault topic isolation text file shows cmd_vel, odom, and AMCL
  publishers/subscribers after the target robot fault.
- This does not prove physical hardware fault recovery; it proves software and
  communication isolation in the ROS2/DDS simulation.

## RPP versus DWB Controller Comparison

This experiment compares the existing Regulated Pure Pursuit controller against
Nav2 DWB without editing the working source YAML files. Both temporary overlays
use the same maps, missions, speed limit (`0.25 m/s`), and inflation radius
(`0.40 m`). Both overlays also use the same `0.30 m` position tolerance and
`1.0 s` controller failure tolerance. These benchmark-only settings prevent a
controller from being classified as failed at a machine pose because of a few
millimetres of costmap discretization; the installed working Nav2 YAML files
are not modified.

Run a one-repeat smoke test on Layout 1 first:

```bash
cd ~/dual_robot_ws/fyp_testing
./scripts/run_controller_comparison.sh 1 1 240 gui
```

If both RPP and DWB complete, run the final comparison on Layouts 1 and 4:

```bash
./scripts/run_controller_comparison.sh 1,4 5 300 gui
```

Pilot/smoke-test runs are automatically replaced in the aggregate CSV when a
new run uses the same layout, repeat, controller, and robot. Run the smoke test
again after changing benchmark parameters before collecting the five final
repeats.

The runner alternates controller order between repeats and creates:

```text
results/csv/controller_comparison_runs.csv
results/csv/controller_comparison_summary.csv
results/csv/controller_comparison_statistics.csv
results/plots/controller_rpp_vs_dwb.png
```

To regenerate the controller summaries without repeating simulations:

```bash
python3 scripts/aggregate_controller_comparison.py \
  --master results/csv/navigation_metrics.csv \
  --output-dir results/csv \
  --plots-dir results/plots
```

## Analyze An Existing Bag

Dual:

```bash
./scripts/analyze_rosbag.py results/bags/dual_layout1_r1_example \
  --mode dual \
  --layout 1 \
  --repeat 1 \
  --success true \
  --output results/csv/example_dual_metrics.csv
```

Single:

```bash
./scripts/analyze_rosbag.py results/bags/single_layout1_r1_example \
  --mode single \
  --layout 1 \
  --repeat 1 \
  --success true \
  --output results/csv/example_single_metrics.csv
```

## Aggregate CSV Results

```bash
./scripts/aggregate_results.py \
  --csv-dir results/csv \
  --output-dir results/csv
```

This creates:

```text
results/csv/navigation_metrics.csv
results/csv/single_vs_dual.csv
results/csv/inflation_radius_results.csv
results/csv/layout_summary.csv
```

## CSV Columns

Main metrics CSV:

```text
run_id,mode,layout,repeat,inflation_radius,robot,bag_path,success,
mission_time_s,path_length_m,odom_msg_count,cmd_vel_msg_count,plan_count,
recovery_count,amcl_mean_error_m,amcl_rmse_m,notes
```

Single vs dual CSV:

```text
layout,repeat,inflation_radius,single_time_s,dual_time_s,efficiency_gain_pct
```

Efficiency gain is calculated as:

```text
(Single_time - Dual_time) / Single_time * 100
```

## Assumptions

- Path length is calculated from odometry positions.
- Mission time is calculated from the first to last relevant recorded robot message.
- Dual mission time for comparison uses the slower robot because the parallel mission completes when both robots are finished.
- AMCL localization error is calculated only if `/gazebo/model_states` exists in the bag.
- Recovery count is best-effort from `/rosout` messages containing recovery-related keywords.
- DWA vs TEB is not automated because the current project uses DWB and no safe TEB config was found.
