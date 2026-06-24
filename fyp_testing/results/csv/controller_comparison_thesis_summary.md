# RPP versus DWB Controller Comparison

Five paired simulation repeats were performed per layout using identical missions,
speed limits, inflation radius, goal tolerance, and controller failure tolerance.

| Layout | RPP makespan, mean +/- SD (s) | DWB makespan, mean +/- SD (s) | RPP time reduction | 95% CI of DWB-RPP (s) | p-value | Cohen's dz |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 73.689 +/- 0.825 | 88.168 +/- 7.489 | 15.98% | [5.579, 23.379] | 0.01068225 | 2.020 |
| 4 | 67.338 +/- 0.230 | 77.177 +/- 0.291 | 12.75% | [9.442, 10.236] | 0.00000027 | 30.776 |

## Interpretation

- Both controllers completed every measured run, so the comparison concerns efficiency and consistency rather than basic feasibility.
- Positive DWB-RPP confidence intervals mean RPP had a lower mission makespan in every tested layout.
- Layout 1 produced greater DWB variability; one run executed two recovery behaviors and another followed a longer path without a formal recovery.
- These results support a project-specific conclusion for the tested FMS layouts and parameters; they do not establish that RPP is universally superior to DWB.
- Report the paired test, confidence interval, effect size, success rate, and path-length result together. Do not report only the p-value.
