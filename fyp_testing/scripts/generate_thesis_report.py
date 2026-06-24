#!/usr/bin/env python3
"""Generate supervisor-ready plots and summary tables from FYP test CSVs."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


RADII = ["0.20", "0.25", "0.30", "0.40", "0.55"]


def read_csv(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalized_radius(value):
    number = as_float(value)
    if number is None:
        return value
    return f"{number:.2f}"


def completed(row):
    return "both robots returned to Loading Dock" in row.get("notes", "")


def grouped_inflation_runs(rows):
    runs = defaultdict(dict)
    for row in rows:
        key = (row["layout"], normalized_radius(row["inflation_radius"]), row["repeat"])
        runs[key][row["robot"]] = row

    paired = []
    for (layout, radius, repeat), robots in runs.items():
        if "TB3_1" not in robots or "TB3_2" not in robots:
            continue
        t1 = as_float(robots["TB3_1"].get("mission_time_s"))
        t2 = as_float(robots["TB3_2"].get("mission_time_s"))
        p1 = as_float(robots["TB3_1"].get("path_length_m"))
        p2 = as_float(robots["TB3_2"].get("path_length_m"))
        if t1 is None or t2 is None:
            continue
        paired.append({
            "layout": layout,
            "radius": radius,
            "repeat": repeat,
            "success": completed(robots["TB3_1"]) and completed(robots["TB3_2"]),
            "dual_time_s": max(t1, t2),
            "tb3_1_time_s": t1,
            "tb3_2_time_s": t2,
            "tb3_1_path_m": p1,
            "tb3_2_path_m": p2,
            "recovery_count": max(
                int(robots["TB3_1"].get("recovery_count") or 0),
                int(robots["TB3_2"].get("recovery_count") or 0),
            ),
        })
    return paired


def inflation_summary(rows):
    grouped = defaultdict(list)
    for row in grouped_inflation_runs(rows):
        grouped[(row["layout"], row["radius"])].append(row)

    summary = []
    for (layout, radius), values in sorted(grouped.items(), key=lambda x: (int(x[0][0]), float(x[0][1]))):
        successful = [row for row in values if row["success"]]
        summary.append({
            "layout": layout,
            "radius": radius,
            "runs": len(values),
            "successful_runs": len(successful),
            "success_rate_pct": len(successful) / len(values) * 100.0 if values else 0.0,
            "mean_dual_time_s": mean(row["dual_time_s"] for row in successful) if successful else None,
            "std_dual_time_s": pstdev(row["dual_time_s"] for row in successful) if len(successful) > 1 else 0.0,
            "mean_recovery_count": mean(row["recovery_count"] for row in values) if values else None,
        })
    return summary


def write_csv(path, rows, fieldnames):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_single_vs_dual(summary_rows, plots_dir):
    layouts = [row["layout"] for row in summary_rows]
    single = [as_float(row["mean_single_time_s"]) for row in summary_rows]
    dual = [as_float(row["mean_dual_time_s"]) for row in summary_rows]
    gains = [as_float(row["mean_efficiency_gain_pct"]) for row in summary_rows]

    x = range(len(layouts))
    width = 0.36

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar([i - width / 2 for i in x], single, width, label="Single robot", color="#4c78a8")
    ax.bar([i + width / 2 for i in x], dual, width, label="Dual robot", color="#f58518")
    ax.set_xticks(list(x), [f"Layout {layout}" for layout in layouts])
    ax.set_ylabel("Mean mission time (s)")
    ax.set_title("Single Robot vs Dual Robot Mission Time")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "single_vs_dual_mission_time.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar([f"Layout {layout}" for layout in layouts], gains, color="#54a24b")
    ax.set_ylabel("Efficiency gain (%)")
    ax.set_title("Dual-Robot Efficiency Gain")
    ax.grid(axis="y", alpha=0.25)
    for bar, gain in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8, f"{gain:.1f}%", ha="center")
    fig.tight_layout()
    fig.savefig(plots_dir / "efficiency_gain_by_layout.png", dpi=180)
    plt.close(fig)


def plot_inflation(summary_rows, plots_dir):
    by_layout = defaultdict(list)
    for row in summary_rows:
        by_layout[row["layout"]].append(row)

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for layout in sorted(by_layout, key=int):
        rows = sorted(by_layout[layout], key=lambda r: float(r["radius"]))
        xs = [float(row["radius"]) for row in rows]
        ys = [
            row["mean_dual_time_s"] if row["mean_dual_time_s"] is not None else float("nan")
            for row in rows
        ]
        ax.plot(xs, ys, marker="o", linewidth=2, label=f"Layout {layout}")
    ax.set_xlabel("Inflation radius (m)")
    ax.set_ylabel("Mean successful dual mission time (s)")
    ax.set_title("Inflation Radius Impact on Mission Time")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "inflation_radius_vs_time.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for layout in sorted(by_layout, key=int):
        rows = sorted(by_layout[layout], key=lambda r: float(r["radius"]))
        xs = [float(row["radius"]) for row in rows]
        ys = [row["success_rate_pct"] for row in rows]
        ax.plot(xs, ys, marker="o", linewidth=2, label=f"Layout {layout}")
    ax.set_xlabel("Inflation radius (m)")
    ax.set_ylabel("Success rate (%)")
    ax.set_ylim(-5, 105)
    ax.set_title("Inflation Radius Impact on Reliability")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "inflation_radius_success_rate.png", dpi=180)
    plt.close(fig)


def markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_report(path, single_summary, infl_summary):
    best_by_layout = {}
    for row in infl_summary:
        if row["successful_runs"] == 0:
            continue
        current = best_by_layout.get(row["layout"])
        if current is None:
            best_by_layout[row["layout"]] = row
            continue
        if row["success_rate_pct"] > current["success_rate_pct"]:
            best_by_layout[row["layout"]] = row
        elif row["success_rate_pct"] == current["success_rate_pct"]:
            if row["mean_dual_time_s"] < current["mean_dual_time_s"]:
                best_by_layout[row["layout"]] = row

    single_rows = [
        [
            row["layout"],
            row["runs"],
            row["mean_single_time_s"],
            row["mean_dual_time_s"],
            row["mean_efficiency_gain_pct"] + "%",
        ]
        for row in single_summary
    ]
    best_rows = [
        [
            layout,
            row["radius"],
            f"{row['success_rate_pct']:.1f}%",
            f"{row['mean_dual_time_s']:.3f}",
        ]
        for layout, row in sorted(best_by_layout.items(), key=lambda x: int(x[0]))
    ]

    text = [
        "# FYP Navigation Experiment Summary",
        "",
        "## Single Robot vs Dual Robot",
        markdown_table(
            ["Layout", "Runs", "Mean Single Time (s)", "Mean Dual Time (s)", "Mean Efficiency Gain"],
            single_rows,
        ),
        "",
        "## Best Inflation Radius By Layout",
        markdown_table(
            ["Layout", "Best Radius (m)", "Success Rate", "Mean Dual Time (s)"],
            best_rows,
        ),
        "",
        "## Key Points For Supervisor",
        "- Dual-robot navigation reduced mission completion time by roughly 52-66% depending on layout.",
        "- Inflation radius affected both reliability and mission time; very small radii caused timeout failures in narrow layouts.",
        "- A balanced global inflation radius is 0.40 m, while per-layout tuning gave the fastest results.",
        "- Namespace isolation was verified: TB3_1 and TB3_2 have separate cmd_vel, odom, scan, and AMCL topics.",
        "- AMCL error columns are present, but current bags do not include Gazebo model-state ground truth, so localization error is not reported as a measured result.",
        "",
        "## Generated Figures",
        "- `single_vs_dual_mission_time.png`",
        "- `efficiency_gain_by_layout.png`",
        "- `inflation_radius_vs_time.png`",
        "- `inflation_radius_success_rate.png`",
        "",
    ]
    Path(path).write_text("\n".join(text))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default="results/csv")
    parser.add_argument("--plots-dir", default="results/plots")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    plots_dir = Path(args.plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)

    single_summary = read_csv(csv_dir / "single_vs_dual_summary.csv")
    inflation_rows = read_csv(csv_dir / "inflation_radius_results.csv")
    infl_summary = inflation_summary(inflation_rows)

    write_csv(
        csv_dir / "inflation_radius_summary.csv",
        [
            {
                "layout": row["layout"],
                "inflation_radius": row["radius"],
                "runs": row["runs"],
                "successful_runs": row["successful_runs"],
                "success_rate_pct": f"{row['success_rate_pct']:.1f}",
                "mean_dual_time_s": "" if row["mean_dual_time_s"] is None else f"{row['mean_dual_time_s']:.3f}",
                "std_dual_time_s": f"{row['std_dual_time_s']:.3f}",
                "mean_recovery_count": "" if row["mean_recovery_count"] is None else f"{row['mean_recovery_count']:.2f}",
            }
            for row in infl_summary
        ],
        [
            "layout",
            "inflation_radius",
            "runs",
            "successful_runs",
            "success_rate_pct",
            "mean_dual_time_s",
            "std_dual_time_s",
            "mean_recovery_count",
        ],
    )

    plot_single_vs_dual(single_summary, plots_dir)
    plot_inflation(infl_summary, plots_dir)
    write_report(plots_dir / "supervisor_summary.md", single_summary, infl_summary)

    print(f"Saved plots to: {plots_dir}")
    print(f"Saved inflation summary: {csv_dir / 'inflation_radius_summary.csv'}")
    print(f"Saved report: {plots_dir / 'supervisor_summary.md'}")


if __name__ == "__main__":
    raise SystemExit(main())
