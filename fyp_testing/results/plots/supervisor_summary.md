# FYP Navigation Experiment Summary

## Single Robot vs Dual Robot
| Layout | Runs | Mean Single Time (s) | Mean Dual Time (s) | Mean Efficiency Gain |
| ---    | ---  | ---                  | ---                | ---                  |
| 1      | 5    | 194.736              | 79.780             | 58.85%               | 
| 2      | 5    | 176.621              | 74.680             | 57.67%               |
| 3      | 5    | 156.836              | 52.030             | 66.37%               |
| 4      | 5    | 154.108              | 73.750             | 52.12%               |

## Best Inflation Radius By Layout
| Layout | Best Radius (m) | Success Rate | Mean Dual Time (s) |
| ---    | ---             | ---          | ---                |
| 1      | 0.40            | 100.0%       | 75.899             |
| 2      | 0.30            | 100.0%       | 75.319             |
| 3      | 0.25            | 100.0%       | 49.870             |
| 4      | 0.30            | 100.0%       | 67.920             |

## Key Points For Supervisor
- Dual-robot navigation reduced mission completion time by roughly 52-66% depending on layout.
- Inflation radius affected both reliability and mission time; very small radii caused timeout failures in narrow layouts.
- A balanced global inflation radius is 0.40 m, while per-layout tuning gave the fastest results.
- Namespace isolation was verified: TB3_1 and TB3_2 have separate cmd_vel, odom, scan, and AMCL topics.
- AMCL error columns are present, but current bags do not include Gazebo model-state ground truth, so localization error is not reported as a measured result.

## Generated Figures
- `single_vs_dual_mission_time.png`
- `efficiency_gain_by_layout.png`
- `inflation_radius_vs_time.png`
- `inflation_radius_success_rate.png`
