#!/usr/bin/env python3
"""Aggregate per-run navigation metrics into thesis summary CSV files."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean


def read_master(csv_dir):
    master = Path(csv_dir) / "navigation_metrics.csv"
    if not master.exists():
        raise FileNotFoundError(f"Missing master CSV: {master}")
    with master.open(newline="") as handle:
        return list(csv.DictReader(handle))


def time_value(row):
    try:
        return float(row["mission_time_s"])
    except (TypeError, ValueError):
        return None


def run_stamp(row):
    return row.get("run_id", "")


def latest_default_rows(rows):
    latest = {}
    for row in rows:
        if row.get("inflation_radius") != "default":
            continue
        key = (
            row.get("mode", ""),
            row.get("layout", ""),
            row.get("repeat", ""),
            row.get("inflation_radius", ""),
            row.get("robot", ""),
        )
        if key not in latest or run_stamp(row) > run_stamp(latest[key]):
            latest[key] = row
    return list(latest.values())


def write_single_vs_dual(rows, output_dir):
    single_times = {}
    dual_times = defaultdict(list)

    for row in latest_default_rows(rows):
        key = (row["layout"], row["repeat"], row["inflation_radius"])
        value = time_value(row)
        if value is None:
            continue
        if row["mode"] == "single":
            single_times[key] = value
        elif row["mode"] == "dual":
            dual_times[key].append(value)

    out = Path(output_dir) / "single_vs_dual.csv"
    with out.open("w", newline="") as handle:
        fieldnames = [
            "layout",
            "repeat",
            "inflation_radius",
            "single_time_s",
            "dual_time_s",
            "efficiency_gain_pct",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key, single_time in sorted(single_times.items()):
            dual_values = dual_times.get(key)
            if not dual_values:
                continue
            dual_time = max(dual_values)
            gain = (single_time - dual_time) / single_time * 100.0
            writer.writerow({
                "layout": key[0],
                "repeat": key[1],
                "inflation_radius": key[2],
                "single_time_s": f"{single_time:.3f}",
                "dual_time_s": f"{dual_time:.3f}",
                "efficiency_gain_pct": f"{gain:.2f}",
            })


def write_single_vs_dual_summary(rows, output_dir):
    comparison = []
    single_times = {}
    dual_times = defaultdict(list)

    for row in latest_default_rows(rows):
        key = (row["layout"], row["repeat"], row["inflation_radius"])
        value = time_value(row)
        if value is None:
            continue
        if row["mode"] == "single":
            single_times[key] = value
        elif row["mode"] == "dual":
            dual_times[key].append(value)

    for key, single_time in single_times.items():
        dual_values = dual_times.get(key)
        if not dual_values:
            continue
        dual_time = max(dual_values)
        comparison.append({
            "layout": key[0],
            "single_time_s": single_time,
            "dual_time_s": dual_time,
            "efficiency_gain_pct": (single_time - dual_time) / single_time * 100.0,
        })

    groups = defaultdict(list)
    for row in comparison:
        groups[row["layout"]].append(row)

    out = Path(output_dir) / "single_vs_dual_summary.csv"
    with out.open("w", newline="") as handle:
        fieldnames = [
            "layout",
            "runs",
            "mean_single_time_s",
            "mean_dual_time_s",
            "mean_efficiency_gain_pct",
            "min_efficiency_gain_pct",
            "max_efficiency_gain_pct",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for layout, values in sorted(groups.items(), key=lambda item: int(item[0])):
            gains = [row["efficiency_gain_pct"] for row in values]
            writer.writerow({
                "layout": layout,
                "runs": len(values),
                "mean_single_time_s": f"{mean(row['single_time_s'] for row in values):.3f}",
                "mean_dual_time_s": f"{mean(row['dual_time_s'] for row in values):.3f}",
                "mean_efficiency_gain_pct": f"{mean(gains):.2f}",
                "min_efficiency_gain_pct": f"{min(gains):.2f}",
                "max_efficiency_gain_pct": f"{max(gains):.2f}",
            })


def write_inflation(rows, output_dir):
    out = Path(output_dir) / "inflation_radius_results.csv"
    with out.open("w", newline="") as handle:
        fieldnames = [
            "layout",
            "repeat",
            "inflation_radius",
            "mode",
            "robot",
            "success",
            "mission_time_s",
            "path_length_m",
            "recovery_count",
            "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            try:
                float(row["inflation_radius"])
            except (TypeError, ValueError):
                continue
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_layout_summary(rows, output_dir):
    groups = defaultdict(list)
    for row in rows:
        value = time_value(row)
        if value is not None:
            groups[(row["mode"], row["layout"], row["inflation_radius"], row["robot"])].append(value)

    out = Path(output_dir) / "layout_summary.csv"
    with out.open("w", newline="") as handle:
        fieldnames = [
            "mode",
            "layout",
            "inflation_radius",
            "robot",
            "runs",
            "mean_time_s",
            "min_time_s",
            "max_time_s",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key, values in sorted(groups.items()):
            writer.writerow({
                "mode": key[0],
                "layout": key[1],
                "inflation_radius": key[2],
                "robot": key[3],
                "runs": len(values),
                "mean_time_s": f"{sum(values) / len(values):.3f}",
                "min_time_s": f"{min(values):.3f}",
                "max_time_s": f"{max(values):.3f}",
            })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_master(args.csv_dir)
    write_single_vs_dual(rows, output_dir)
    write_single_vs_dual_summary(rows, output_dir)
    write_inflation(rows, output_dir)
    write_layout_summary(rows, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
