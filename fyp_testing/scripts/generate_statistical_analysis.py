#!/usr/bin/env python3
"""Generate thesis-ready statistical evidence from completed FYP experiments."""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib.pyplot as plt
from scipy import stats


def read_csv(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def confidence_interval(values, confidence=0.95):
    if len(values) < 2:
        return mean(values), mean(values)
    center = mean(values)
    sem = stats.sem(values)
    half_width = stats.t.ppf((1.0 + confidence) / 2.0, len(values) - 1) * sem
    return center - half_width, center + half_width


def paired_effect_size(differences):
    if len(differences) < 2:
        return float("nan")
    spread = stdev(differences)
    return mean(differences) / spread if spread > 0 else float("inf")


def analyze_single_vs_dual(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["layout"]].append(row)

    output = []
    for layout, values in sorted(grouped.items(), key=lambda item: int(item[0])):
        values.sort(key=lambda row: int(row["repeat"]))
        single = [float(row["single_time_s"]) for row in values]
        dual = [float(row["dual_time_s"]) for row in values]
        differences = [s - d for s, d in zip(single, dual)]
        gains = [float(row["efficiency_gain_pct"]) for row in values]

        diff_low, diff_high = confidence_interval(differences)
        gain_low, gain_high = confidence_interval(gains)
        paired_t = stats.ttest_rel(single, dual)
        try:
            wilcoxon = stats.wilcoxon(single, dual, alternative="greater")
            wilcoxon_p = wilcoxon.pvalue
        except ValueError:
            wilcoxon_p = float("nan")

        output.append({
            "layout": layout,
            "paired_runs": len(values),
            "mean_single_time_s": f"{mean(single):.3f}",
            "sd_single_time_s": f"{stdev(single):.3f}",
            "mean_dual_time_s": f"{mean(dual):.3f}",
            "sd_dual_time_s": f"{stdev(dual):.3f}",
            "mean_time_saved_s": f"{mean(differences):.3f}",
            "time_saved_95ci_low_s": f"{diff_low:.3f}",
            "time_saved_95ci_high_s": f"{diff_high:.3f}",
            "mean_efficiency_gain_pct": f"{mean(gains):.2f}",
            "efficiency_95ci_low_pct": f"{gain_low:.2f}",
            "efficiency_95ci_high_pct": f"{gain_high:.2f}",
            "paired_t_statistic": f"{paired_t.statistic:.4f}",
            "paired_t_p_value": f"{paired_t.pvalue:.6f}",
            "wilcoxon_one_sided_p_value": f"{wilcoxon_p:.6f}",
            "cohen_dz": f"{paired_effect_size(differences):.3f}",
        })
    return output


def wilson_interval(successes, trials, confidence=0.95):
    if trials == 0:
        return 0.0, 0.0
    z = stats.norm.ppf((1.0 + confidence) / 2.0)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * trials)) / trials) / denominator
    return center - half, center + half


def analyze_inflation_success(rows):
    output = []
    for row in rows:
        trials = int(row["runs"])
        successes = int(row["successful_runs"])
        low, high = wilson_interval(successes, trials)
        output.append({
            "layout": row["layout"],
            "inflation_radius": row["inflation_radius"],
            "runs": trials,
            "successful_runs": successes,
            "success_rate_pct": row["success_rate_pct"],
            "success_95ci_low_pct": f"{low * 100.0:.1f}",
            "success_95ci_high_pct": f"{high * 100.0:.1f}",
            "mean_dual_time_s": row["mean_dual_time_s"],
            "std_dual_time_s": row["std_dual_time_s"],
        })
    return output


def write_csv(path, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_efficiency(rows, output):
    layouts = [f"Layout {row['layout']}" for row in rows]
    means = [float(row["mean_efficiency_gain_pct"]) for row in rows]
    lower = [m - float(row["efficiency_95ci_low_pct"]) for m, row in zip(means, rows)]
    upper = [float(row["efficiency_95ci_high_pct"]) - m for m, row in zip(means, rows)]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(layouts, means, color="#3977a8", yerr=[lower, upper], capsize=6)
    ax.set_ylabel("Efficiency gain (%)")
    ax.set_title("Dual-Robot Efficiency Gain with 95% Confidence Intervals")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.0, f"{value:.1f}%", ha="center")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default="results/csv")
    parser.add_argument("--plots-dir", default="results/plots")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    plots_dir = Path(args.plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)

    comparison = analyze_single_vs_dual(read_csv(csv_dir / "single_vs_dual.csv"))
    inflation = analyze_inflation_success(read_csv(csv_dir / "inflation_radius_summary.csv"))

    comparison_out = csv_dir / "single_vs_dual_statistics.csv"
    inflation_out = csv_dir / "inflation_success_confidence_intervals.csv"
    plot_out = plots_dir / "efficiency_gain_95ci.png"

    write_csv(comparison_out, comparison)
    write_csv(inflation_out, inflation)
    plot_efficiency(comparison, plot_out)

    print(f"Saved: {comparison_out}")
    print(f"Saved: {inflation_out}")
    print(f"Saved: {plot_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
