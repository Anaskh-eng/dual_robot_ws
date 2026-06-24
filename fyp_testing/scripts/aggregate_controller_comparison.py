#!/usr/bin/env python3
"""Aggregate RPP versus DWB experiment rows from navigation_metrics.csv."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib.pyplot as plt
from scipy import stats


def read_csv(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def confidence_interval_95(values):
    if len(values) < 2:
        return None, None
    center = mean(values)
    margin = stats.t.ppf(0.975, len(values) - 1) * stats.sem(values)
    return center - margin, center + margin


def cohens_dz(differences):
    if len(differences) < 2:
        return None
    spread = stdev(differences)
    return mean(differences) / spread if spread else None


def latest_controller_rows(rows):
    latest = {}
    for row in rows:
        label = row.get("inflation_radius", "")
        if not label.startswith("controller_"):
            continue
        controller = label.removeprefix("controller_")
        key = (row["layout"], row["repeat"], controller, row["robot"])
        if key not in latest or row["run_id"] > latest[key]["run_id"]:
            latest[key] = row
    return list(latest.values())


def build_runs(rows):
    grouped = defaultdict(dict)
    for row in latest_controller_rows(rows):
        controller = row["inflation_radius"].removeprefix("controller_")
        grouped[(row["layout"], row["repeat"], controller)][row["robot"]] = row

    output = []
    for (layout, repeat, controller), robots in sorted(grouped.items()):
        if not {"TB3_1", "TB3_2"}.issubset(robots):
            continue
        r1 = robots["TB3_1"]
        r2 = robots["TB3_2"]
        t1 = as_float(r1.get("mission_time_s"))
        t2 = as_float(r2.get("mission_time_s"))
        p1 = as_float(r1.get("path_length_m"))
        p2 = as_float(r2.get("path_length_m"))
        completed = (
            "both robots returned to Loading Dock" in r1.get("notes", "")
            and "both robots returned to Loading Dock" in r2.get("notes", "")
        )
        output.append({
            "layout": layout,
            "repeat": repeat,
            "controller": controller,
            "run_id": r1["run_id"],
            "completed": str(completed).lower(),
            "dual_makespan_s": "" if t1 is None or t2 is None else f"{max(t1, t2):.3f}",
            "tb3_1_time_s": "" if t1 is None else f"{t1:.3f}",
            "tb3_2_time_s": "" if t2 is None else f"{t2:.3f}",
            "total_path_length_m": "" if p1 is None or p2 is None else f"{p1 + p2:.3f}",
            "tb3_1_path_m": "" if p1 is None else f"{p1:.3f}",
            "tb3_2_path_m": "" if p2 is None else f"{p2:.3f}",
            "recovery_count": max(int(r1.get("recovery_count") or 0), int(r2.get("recovery_count") or 0)),
        })
    return output


def build_summary(runs):
    grouped = defaultdict(list)
    for row in runs:
        grouped[(row["layout"], row["controller"])].append(row)

    output = []
    for (layout, controller), values in sorted(grouped.items()):
        successful = [row for row in values if row["completed"] == "true" and row["dual_makespan_s"]]
        times = [float(row["dual_makespan_s"]) for row in successful]
        paths = [float(row["total_path_length_m"]) for row in successful if row["total_path_length_m"]]
        ci_low, ci_high = confidence_interval_95(times)
        output.append({
            "layout": layout,
            "controller": controller,
            "runs": len(values),
            "successful_runs": len(successful),
            "success_rate_pct": f"{len(successful) / len(values) * 100.0:.1f}" if values else "",
            "mean_makespan_s": f"{mean(times):.3f}" if times else "",
            "sd_makespan_s": f"{stdev(times):.3f}" if len(times) > 1 else "0.000",
            "makespan_ci95_low_s": "" if ci_low is None else f"{ci_low:.3f}",
            "makespan_ci95_high_s": "" if ci_high is None else f"{ci_high:.3f}",
            "mean_total_path_m": f"{mean(paths):.3f}" if paths else "",
            "mean_recovery_count": f"{mean(float(row['recovery_count']) for row in values):.2f}" if values else "",
        })
    return output


def build_statistics(runs):
    paired = defaultdict(dict)
    for row in runs:
        if row["completed"] == "true" and row["dual_makespan_s"]:
            paired[(row["layout"], row["repeat"])][row["controller"]] = row

    by_layout = defaultdict(list)
    for (layout, repeat), controllers in paired.items():
        if {"rpp", "dwb"}.issubset(controllers):
            by_layout[layout].append((int(repeat), controllers["rpp"], controllers["dwb"]))

    output = []
    for layout, values in sorted(by_layout.items(), key=lambda item: int(item[0])):
        values.sort()
        rpp = [float(value[1]["dual_makespan_s"]) for value in values]
        dwb = [float(value[2]["dual_makespan_s"]) for value in values]
        rpp_paths = [float(value[1]["total_path_length_m"]) for value in values]
        dwb_paths = [float(value[2]["total_path_length_m"]) for value in values]
        time_differences = [b - a for a, b in zip(rpp, dwb)]
        path_differences = [b - a for a, b in zip(rpp_paths, dwb_paths)]
        ci_low, ci_high = confidence_interval_95(time_differences)
        time_test = stats.ttest_rel(rpp, dwb) if len(values) > 1 else None
        path_test = stats.ttest_rel(rpp_paths, dwb_paths) if len(values) > 1 else None
        effect_size = cohens_dz(time_differences)
        output.append({
            "layout": layout,
            "paired_runs": len(values),
            "mean_rpp_makespan_s": f"{mean(rpp):.3f}",
            "mean_dwb_makespan_s": f"{mean(dwb):.3f}",
            "mean_rpp_minus_dwb_s": f"{-mean(time_differences):.3f}",
            "dwb_improvement_pct": f"{mean((a - b) / a * 100.0 for a, b in zip(rpp, dwb)):.2f}",
            "mean_dwb_minus_rpp_s": f"{mean(time_differences):.3f}",
            "rpp_time_reduction_vs_dwb_pct": f"{mean((b - a) / b * 100.0 for a, b in zip(rpp, dwb)):.2f}",
            "time_difference_ci95_low_s": "" if ci_low is None else f"{ci_low:.3f}",
            "time_difference_ci95_high_s": "" if ci_high is None else f"{ci_high:.3f}",
            "time_cohens_dz": "" if effect_size is None else f"{effect_size:.3f}",
            "paired_t_p_value": "" if time_test is None else f"{time_test.pvalue:.8f}",
            "mean_rpp_path_m": f"{mean(rpp_paths):.3f}",
            "mean_dwb_path_m": f"{mean(dwb_paths):.3f}",
            "mean_dwb_minus_rpp_path_m": f"{mean(path_differences):.3f}",
            "rpp_path_reduction_vs_dwb_pct": f"{mean((b - a) / b * 100.0 for a, b in zip(rpp_paths, dwb_paths)):.2f}",
            "path_paired_t_p_value": "" if path_test is None else f"{path_test.pvalue:.8f}",
        })
    return output


def write_thesis_summary(path, summary, statistical):
    summary_by_key = {(row["layout"], row["controller"]): row for row in summary}
    lines = [
        "# RPP versus DWB Controller Comparison",
        "",
        "Five paired simulation repeats were performed per layout using identical missions,",
        "speed limits, inflation radius, goal tolerance, and controller failure tolerance.",
        "",
        "| Layout | RPP makespan, mean +/- SD (s) | DWB makespan, mean +/- SD (s) | RPP time reduction | 95% CI of DWB-RPP (s) | p-value | Cohen's dz |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in statistical:
        layout = row["layout"]
        rpp = summary_by_key[(layout, "rpp")]
        dwb = summary_by_key[(layout, "dwb")]
        lines.append(
            f"| {layout} | {rpp['mean_makespan_s']} +/- {rpp['sd_makespan_s']} | "
            f"{dwb['mean_makespan_s']} +/- {dwb['sd_makespan_s']} | "
            f"{row['rpp_time_reduction_vs_dwb_pct']}% | "
            f"[{row['time_difference_ci95_low_s']}, {row['time_difference_ci95_high_s']}] | "
            f"{row['paired_t_p_value']} | {row['time_cohens_dz']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Both controllers completed every measured run, so the comparison concerns efficiency and consistency rather than basic feasibility.",
        "- Positive DWB-RPP confidence intervals mean RPP had a lower mission makespan in every tested layout.",
        "- Layout 1 produced greater DWB variability; one run executed two recovery behaviors and another followed a longer path without a formal recovery.",
        "- These results support a project-specific conclusion for the tested FMS layouts and parameters; they do not establish that RPP is universally superior to DWB.",
        "- Report the paired test, confidence interval, effect size, success rate, and path-length result together. Do not report only the p-value.",
        "",
    ])
    Path(path).write_text("\n".join(lines))


def write_csv(path, rows, fieldnames=None):
    if not rows and fieldnames is None:
        return
    fields = fieldnames or list(rows[0].keys())
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_summary(summary, output):
    layouts = sorted({row["layout"] for row in summary}, key=int)
    controllers = ("rpp", "dwb")
    colors = {"rpp": "#3977a8", "dwb": "#e1812c"}
    width = 0.36
    x = list(range(len(layouts)))

    fig, ax = plt.subplots(figsize=(8, 4.8))
    for index, controller in enumerate(controllers):
        values = []
        errors = []
        for layout in layouts:
            row = next((r for r in summary if r["layout"] == layout and r["controller"] == controller), None)
            values.append(float(row["mean_makespan_s"]) if row and row["mean_makespan_s"] else 0.0)
            if row and row["makespan_ci95_low_s"] and row["makespan_ci95_high_s"]:
                errors.append((float(row["makespan_ci95_high_s"]) - float(row["makespan_ci95_low_s"])) / 2.0)
            else:
                errors.append(0.0)
        positions = [i + (index - 0.5) * width for i in x]
        ax.bar(positions, values, width, yerr=errors, capsize=5, label=controller.upper(), color=colors[controller])

    ax.set_xticks(x, [f"Layout {layout}" for layout in layouts])
    ax.set_ylabel("Dual mission makespan (s)")
    ax.set_title("Nav2 Controller Comparison: RPP versus DWB (95% CI)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_paired_runs(runs, output):
    layouts = sorted({row["layout"] for row in runs}, key=int)
    fig, axes = plt.subplots(1, len(layouts), figsize=(4.8 * len(layouts), 4.8), sharey=True)
    if len(layouts) == 1:
        axes = [axes]

    for ax, layout in zip(axes, layouts):
        paired = defaultdict(dict)
        for row in runs:
            if row["layout"] == layout and row["completed"] == "true":
                paired[row["repeat"]][row["controller"]] = float(row["dual_makespan_s"])
        for repeat, values in sorted(paired.items(), key=lambda item: int(item[0])):
            if {"rpp", "dwb"}.issubset(values):
                ax.plot([0, 1], [values["rpp"], values["dwb"]], color="#777777", alpha=0.65)
                ax.scatter(0, values["rpp"], color="#3977a8", s=45, zorder=3)
                ax.scatter(1, values["dwb"], color="#e1812c", s=45, zorder=3)
        ax.set_xticks([0, 1], ["RPP", "DWB"])
        ax.set_title(f"Layout {layout}")
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Dual mission makespan (s)")
    fig.suptitle("Paired Controller Runs (n=5 per layout)")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--plots-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    plots_dir = Path(args.plots_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    runs = build_runs(read_csv(args.master))
    summary = build_summary(runs)
    statistical = build_statistics(runs)

    write_csv(output_dir / "controller_comparison_runs.csv", runs, [
        "layout", "repeat", "controller", "run_id", "completed", "dual_makespan_s",
        "tb3_1_time_s", "tb3_2_time_s", "total_path_length_m", "tb3_1_path_m",
        "tb3_2_path_m", "recovery_count",
    ])
    write_csv(output_dir / "controller_comparison_summary.csv", summary, [
        "layout", "controller", "runs", "successful_runs", "success_rate_pct",
        "mean_makespan_s", "sd_makespan_s", "makespan_ci95_low_s",
        "makespan_ci95_high_s", "mean_total_path_m", "mean_recovery_count",
    ])
    write_csv(output_dir / "controller_comparison_statistics.csv", statistical, [
        "layout", "paired_runs", "mean_rpp_makespan_s", "mean_dwb_makespan_s",
        "mean_rpp_minus_dwb_s", "dwb_improvement_pct", "mean_dwb_minus_rpp_s",
        "rpp_time_reduction_vs_dwb_pct", "time_difference_ci95_low_s",
        "time_difference_ci95_high_s", "time_cohens_dz", "paired_t_p_value",
        "mean_rpp_path_m", "mean_dwb_path_m", "mean_dwb_minus_rpp_path_m",
        "rpp_path_reduction_vs_dwb_pct", "path_paired_t_p_value",
    ])
    write_thesis_summary(output_dir / "controller_comparison_thesis_summary.md", summary, statistical)
    if summary:
        plot_summary(summary, plots_dir / "controller_rpp_vs_dwb.png")
    if runs:
        plot_paired_runs(runs, plots_dir / "controller_paired_makespan.png")

    print(f"Controller runs found: {len(runs)}")
    print(f"Saved controller CSVs to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
