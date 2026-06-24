#!/usr/bin/env python3
"""Analyze ROS 2 bag files and write thesis-friendly navigation metrics CSV."""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

from rclpy.serialization import deserialize_message
import rosbag2_py
from rosidl_runtime_py.utilities import get_message


ROBOT_TOPICS = {
    "dual": {
        "TB3_1": {
            "odom": "/TB3_1/odom",
            "amcl": "/TB3_1/amcl_pose",
            "plan": "/TB3_1/plan",
            "cmd_vel": "/TB3_1/cmd_vel",
        },
        "TB3_2": {
            "odom": "/TB3_2/odom",
            "amcl": "/TB3_2/amcl_pose",
            "plan": "/TB3_2/plan",
            "cmd_vel": "/TB3_2/cmd_vel",
        },
    },
    "single": {
        "turtlebot3": {
            "odom": "/odom",
            "amcl": "/amcl_pose",
            "plan": "/plan",
            "cmd_vel": "/cmd_vel",
        }
    },
}


def point_from_pose_msg(msg):
    return msg.pose.pose.position.x, msg.pose.pose.position.y


def path_length(points):
    if len(points) < 2:
        return 0.0
    total = 0.0
    last = points[0]
    for point in points[1:]:
        total += math.hypot(point[0] - last[0], point[1] - last[1])
        last = point
    return total


def model_name_candidates(robot, mode):
    if mode == "single":
        return ("turtlebot3", "waffle_pi", "burger")
    return (robot, f"/{robot}")


def nearest_ground_truth_error(amcl_samples, truth_samples):
    if not amcl_samples or not truth_samples:
        return "", ""

    errors = []
    j = 0
    for stamp, x_amcl, y_amcl in amcl_samples:
        while j + 1 < len(truth_samples) and abs(truth_samples[j + 1][0] - stamp) < abs(truth_samples[j][0] - stamp):
            j += 1
        _, x_gt, y_gt = truth_samples[j]
        errors.append(math.hypot(x_amcl - x_gt, y_amcl - y_gt))

    mean = sum(errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    return f"{mean:.4f}", f"{rmse:.4f}"


def read_bag(bag_path, mode):
    reader = rosbag2_py.SequentialReader()
    storage_options = rosbag2_py.StorageOptions(uri=str(bag_path), storage_id="sqlite3")
    converter_options = rosbag2_py.ConverterOptions("", "")
    reader.open(storage_options, converter_options)

    topic_types = {
        topic.name: topic.type for topic in reader.get_all_topics_and_types()
    }
    msg_classes = {
        topic: get_message(type_name) for topic, type_name in topic_types.items()
    }

    robot_topics = ROBOT_TOPICS[mode]
    metrics = {
        robot: {
            "odom_points": [],
            "odom_count": 0,
            "amcl_samples": [],
            "cmd_vel_count": 0,
            "plan_count": 0,
            "first_stamp": None,
            "last_stamp": None,
            "first_motion_stamp": None,
            "last_motion_stamp": None,
            "recovery_count": 0,
        }
        for robot in robot_topics
    }
    truth = defaultdict(list)
    def mark_time(robot, stamp):
        item = metrics[robot]
        if item["first_stamp"] is None or stamp < item["first_stamp"]:
            item["first_stamp"] = stamp
        if item["last_stamp"] is None or stamp > item["last_stamp"]:
            item["last_stamp"] = stamp

    def mark_motion(robot, stamp):
        item = metrics[robot]
        if item["first_motion_stamp"] is None or stamp < item["first_motion_stamp"]:
            item["first_motion_stamp"] = stamp
        if item["last_motion_stamp"] is None or stamp > item["last_motion_stamp"]:
            item["last_motion_stamp"] = stamp

    while reader.has_next():
        topic, data, stamp = reader.read_next()
        if topic not in msg_classes:
            continue
        msg = deserialize_message(data, msg_classes[topic])

        if topic == "/rosout":
            text = getattr(msg, "msg", "").lower()
            logger = getattr(msg, "name", "").lower().lstrip("/")
            recovery_started = any(
                marker in text
                for marker in ("running spin", "running backup", "running back_up", "running wait")
            )
            if recovery_started:
                if mode == "single":
                    metrics["turtlebot3"]["recovery_count"] += 1
                else:
                    for robot in metrics:
                        if logger.startswith(robot.lower() + "."):
                            metrics[robot]["recovery_count"] += 1
                            break
            continue

        if topic in ("/gazebo/model_states", "/model_states"):
            for index, name in enumerate(msg.name):
                pose = msg.pose[index]
                truth[name].append((stamp, pose.position.x, pose.position.y))
            continue

        for robot, topics in robot_topics.items():
            if topic == topics["odom"]:
                metrics[robot]["odom_count"] += 1
                metrics[robot]["odom_points"].append(point_from_pose_msg(msg))
                mark_time(robot, stamp)
            elif topic == topics["amcl"]:
                x, y = point_from_pose_msg(msg)
                metrics[robot]["amcl_samples"].append((stamp, x, y))
                mark_time(robot, stamp)
            elif topic == topics["cmd_vel"]:
                metrics[robot]["cmd_vel_count"] += 1
                linear = getattr(msg, "linear", None)
                angular = getattr(msg, "angular", None)
                moving = False
                if linear is not None:
                    moving = moving or abs(linear.x) > 1e-4 or abs(linear.y) > 1e-4
                if angular is not None:
                    moving = moving or abs(angular.z) > 1e-4
                if moving:
                    mark_motion(robot, stamp)
                mark_time(robot, stamp)
            elif topic == topics["plan"]:
                metrics[robot]["plan_count"] += 1
                mark_time(robot, stamp)

    return metrics, truth


def build_rows(args, metrics, truth):
    run_id = Path(args.bag).name
    rows = []
    for robot, item in metrics.items():
        first_stamp = item["first_motion_stamp"] or item["first_stamp"]
        last_stamp = item["last_motion_stamp"] or item["last_stamp"]
        duration = ""
        if first_stamp is not None and last_stamp is not None and last_stamp >= first_stamp:
            duration = f"{(last_stamp - first_stamp) / 1e9:.3f}"

        truth_samples = []
        for candidate in model_name_candidates(robot, args.mode):
            if candidate in truth:
                truth_samples = truth[candidate]
                break

        amcl_mean, amcl_rmse = nearest_ground_truth_error(
            item["amcl_samples"],
            truth_samples,
        )

        rows.append({
            "run_id": run_id,
            "mode": args.mode,
            "layout": args.layout,
            "repeat": args.repeat,
            "inflation_radius": args.inflation_radius,
            "robot": robot,
            "bag_path": str(Path(args.bag).resolve()),
            "success": args.success,
            "mission_time_s": duration,
            "path_length_m": f"{path_length(item['odom_points']):.3f}",
            "odom_msg_count": item["odom_count"],
            "cmd_vel_msg_count": item["cmd_vel_count"],
            "plan_count": item["plan_count"],
            "recovery_count": item["recovery_count"],
            "amcl_mean_error_m": amcl_mean,
            "amcl_rmse_m": amcl_rmse,
            "notes": args.notes,
        })
    return rows


def append_master_csv(output, rows):
    master = output.parent / "navigation_metrics.csv"
    fieldnames = list(rows[0].keys())
    existing = []
    if master.exists():
        with master.open(newline="") as handle:
            existing = [
                {field: row.get(field, "") for field in fieldnames}
                for row in csv.DictReader(handle)
            ]

    replacements = {(row["run_id"], row["robot"]): row for row in rows}
    merged = [
        row for row in existing
        if (row.get("run_id"), row.get("robot")) not in replacements
    ]
    merged.extend(rows)
    temporary = master.with_suffix(master.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)
    temporary.replace(master)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bag", help="Path to a rosbag2 directory")
    parser.add_argument("--mode", choices=("single", "dual"), required=True)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--repeat", required=True)
    parser.add_argument("--inflation-radius", default="default")
    parser.add_argument("--success", default="unknown")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    metrics, truth = read_bag(Path(args.bag), args.mode)
    rows = build_rows(args, metrics, truth)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    append_master_csv(output, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
