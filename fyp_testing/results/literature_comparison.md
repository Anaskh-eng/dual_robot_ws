# Literature Comparison and Thesis Positioning

## Why The Seminar Evidence Looked Weak

The seminar demonstrated a functioning ROS2/Nav2 system and reported useful experimental results, but it did not clearly separate:

1. software components adopted from ROS2/Nav2;
2. engineering work developed in this project;
3. controlled experimental findings produced by this project; and
4. comparison with quantitative findings from prior work.

The thesis should not claim novelty from merely using ROS2, Nav2, Gazebo, or TurtleBot3. The defensible contribution is the designed experimental framework, dual-namespace mission implementation, four-layout benchmark adaptation, repeated parameter study, single-versus-dual evaluation, and fault/namespace validation.

## Quantitative Comparison Matrix

| Study | Platform and task | Reported quantitative evidence | Relationship to this FYP | Valid comparison |
| --- | --- | --- | --- | --- |
| Mahmud et al., 2025, *Dual Robot Path Planning in Simulated Lab-Scaled Flexible Manufacturing System*, ICCAR, DOI 10.1109/ICCAR64901.2025.11073005 | Two TurtleBot3 Waffle Pi robots in Gazebo; FMS with four machines, L/U and charging station; DWA versus TEB | DWA total times: Robot A 114 s, Robot B 96 s. TEB total times: Robot A 78 s, Robot B 84 s. Reported success: DWA 78.88%, TEB 90.12%. | Closest domain benchmark. This FYP uses ROS2 Humble/Nav2, NavFn global planning and Regulated Pure Pursuit control, separate namespaces, repeated runs, four layouts and parallel task allocation. | Contextual only for current data because the route, map scale, controller and task allocation differ. A new matched-route/controller benchmark is needed for a direct comparison. |
| Kaoud et al., *Scheduling of Automated Guided Vehicles and Machines in Flexible Manufacturing Systems: A Simulation Study* | Two identical AGVs and four FMS layouts based on Bilge and Ulusoy benchmark data; discrete-event scheduling and makespan optimization | Published directed travel-time matrices for L/U and M1-M4 in all four layouts; example schedule makespan 166 versus 151 for STW, approximately 9% difference. | The four FYP layouts were adapted from this benchmark topology, but implemented as continuous Gazebo/Nav2 environments. | Compare topology and relative route difficulty. Do not compare raw times without normalization because speed, scale, loading assumptions and simulation type differ. A scale-factor/correlation validation is suitable. |
| Camisa, Testa and Notarstefano, 2023, *Multi-Robot Pickup and Delivery via Distributed Resource Allocation*, IEEE TRO, DOI 10.1109/TRO.2022.3216801 | ROS2/Gazebo distributed pickup-and-delivery; TurtleBot3; Monte Carlo tests and hardware experiments | 50 Monte Carlo trials per robot count; distributed solution reported 30-40% suboptimality; four-TurtleBot3 benchmark matched centralized assignment; larger heterogeneous teams demonstrated. | Supports the importance of distributed task allocation and scalability. This FYP uses a fixed two-way task split rather than distributed optimization. | Qualitative architectural comparison only. Do not compare the FYP's 52-66% time gain with their 30-40% cost suboptimality because the quantities are different. |
| Suresh et al., 2025, *Dual-Robot Occupancy Grid Map Merging: A Study on Warehouse Simulation*, ICCRE, DOI 10.1109/ICCRE65455.2025.11093550 | ROS2 dual-robot warehouse map merging; separate map topics and merged map | Demonstrates merged occupancy-grid construction and ROS2 topic separation; does not report comparable mission completion times. | Supports ROS2 multi-robot topic separation and mapping context. This FYP focuses on navigation performance over known maps. | Qualitative comparison only. It is not a performance baseline for mission time. |
| Macenski et al., 2022/2023, *Robot Operating System 2: Design, Architecture, and Uses in the Wild* | ROS2 architecture review and deployments | Documents DDS peer-to-peer discovery, lifecycle nodes, security, real-time and multi-robot support. | Supports the architectural rationale for ROS2 and the DDS fault-isolation experiment. | Architecture reference, not a navigation-time benchmark. |
| Li et al., 2024, *Intelligent Multi-Robot Collaborative Transport System* | ROS1, FastDDS service, Gazebo collaborative transport | Reports transport target/trajectory errors and system integration; states resilience motivation for multi-robot systems. | Related to the FYP DDS/fault-isolation test, but uses a different transport task and architecture. | Qualitative comparison only unless the same fault metric is replicated. |

## Existing FYP Results With Statistical Evidence

Five paired single/dual runs were completed for each layout. The paired analysis is saved in:

- `results/csv/single_vs_dual_statistics.csv`
- `results/plots/efficiency_gain_95ci.png`

| Layout | Mean single time (s) | Mean dual time (s) | Mean gain | 95% CI for gain | Paired t-test p | Cohen's dz |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 194.736 | 79.780 | 58.85% | 54.78-62.92% | 0.000059 | 7.960 |
| 2 | 176.621 | 74.680 | 57.67% | 55.71-59.64% | 0.000004 | 15.708 |
| 3 | 156.836 | 52.030 | 66.37% | 60.69-72.04% | 0.000297 | 5.269 |
| 4 | 154.108 | 73.750 | 52.12% | 50.75-53.49% | 0.000002 | 19.854 |

The exact one-sided Wilcoxon p-value is 0.03125 for each layout. This is the smallest attainable one-sided exact value with five consistently positive paired differences. The results therefore support a strong improvement, but the thesis must acknowledge that `n=5` gives wide uncertainty for success-rate estimates and that deterministic simulation runs are not equivalent to independent physical trials.

Inflation success-rate Wilson confidence intervals are saved in:

- `results/csv/inflation_success_confidence_intervals.csv`

With only five trials, an observed 100% success rate has a 95% Wilson interval of approximately 56.6-100%. The thesis should report both `5/5` and the interval rather than presenting 100% as certainty.

## Highest-Value Additional Experiment

### ROS2 Controller Benchmark: RPP versus DWB

The current system uses:

- NavFn global planner;
- Regulated Pure Pursuit (RPP) local controller;
- ROS2 Humble/Nav2.

The closest paper compares DWA and TEB under ROS1-style navigation. Nav2 Humble includes DWB, which belongs to the Dynamic Window family. A controlled comparison of the current RPP controller against DWB would demonstrate an actual engineering design decision rather than simple software use.

Recommended design:

1. Keep world, map, waypoints, spawn pose, velocity limits, inflation radius and mission controller fixed.
2. Change only the local controller plugin: RPP versus DWB.
3. Use Layouts 1 and 4 because they represent long-path and constrained/crossing behavior.
4. Run five repeats for each controller and layout: 20 total runs.
5. Record mission makespan, per-robot time, path length, success, recoveries and variability.
6. Report mean, standard deviation, 95% confidence interval and paired/unpaired test as appropriate.

This result can be positioned beside Mahmud et al. (2025): their work compared DWA and TEB, while this project evaluates a ROS2-native Dynamic Window implementation (DWB) against RPP in the adapted benchmark layouts. Raw time values remain contextual unless the same route is reproduced.

## Optional Strong Validation Against The Four Published Layouts

The Kaoud/Bilge-Ulusoy source provides directed travel-time matrices for L/U and M1-M4. A rigorous validation can be added without claiming identical physical time:

1. Execute representative station-to-station routes in each Gazebo layout.
2. Measure Nav2 travel time for each directed edge.
3. Fit one scale factor per layout because Gazebo scale and robot speed differ from the discrete-event benchmark.
4. Compare relative route difficulty using Spearman rank correlation and report normalized MAE or R-squared.

This would directly support the claim that the Gazebo layouts preserve the intended benchmark topology. It is stronger than comparing unrelated total mission times.

## DDS Fault Isolation

The existing fault-injection framework is useful as an additional systems contribution:

- inject a Nav2/controller/localization fault into one robot;
- verify the surviving robot continues publishing odom/cmd_vel;
- verify the surviving robot returns to L/U;
- save post-fault TF and topic-isolation evidence.

Run at least five trials with TB3_1 as target and five with TB3_2 as target. Report survivor completion rate and post-fault completion time. One demonstration run is evidence of functionality, but repeated trials are needed for a result.

## Citation Corrections Needed

The seminar related-work table appears to contain incorrect years:

- The local Mahmud dual-robot FMS paper is 2025, not 2021.
- The local Suresh dual-robot occupancy-grid paper is 2025, not 2023.
- Macenski et al. is the appropriate source for the ROS2 architecture/DDS comparison; it is not a direct navigation benchmark.

Verify every final thesis citation against the PDF title page and DOI before submission.

## Defensible Contribution Statement

Suggested wording:

> This work does not claim novelty in the individual ROS2, Nav2 or Gazebo software components. Its contribution is a reproducible ROS2 Humble dual-robot FMS evaluation framework that integrates namespace-isolated navigation, layout-specific mission allocation, automated rosbag data collection, repeated parameter sensitivity analysis, statistical single-versus-dual evaluation, and software fault-isolation validation across four adapted benchmark layouts.

