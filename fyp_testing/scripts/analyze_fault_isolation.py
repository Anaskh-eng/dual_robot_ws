#!/usr/bin/env python3
"""Summarize dual-robot fault isolation from a fault-injection bag."""

import argparse
import csv
from pathlib import Path

from rclpy.serialization import deserialize_message
import rosbag2_py
from rosidl_runtime_py.utilities import get_message


TOPICS = {
    "TB3_1": {
        "odom": "/TB3_1/odom",
        "cmd_vel": "/TB3_1/cmd_vel",
        "amcl": "/TB3_1/amcl_pose",
    },
    "TB3_2": {
        "odom": "/TB3_2/odom",
        "cmd_vel": "/TB3_2/cmd_vel",
        "amcl": "/TB3_2/amcl_pose",
    },
}


def moving_cmd(msg):
    linear = getattr(msg, "linear", None)
    angular = getattr(msg, "angular", None)
    if linear and (abs(linear.x) > 1e-4 or abs(linear.y) > 1e-4):
        return True
    if angular and abs(angular.z) > 1e-4:
        return True
    return False


def read_bag(bag_path, fault_time_s):
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(bag_path), storage_id="sqlite3"),
        rosbag2_py.ConverterOptions("", ""),
    )

    topic_types = {topic.name: topic.type for topic in reader.get_all_topics_and_types()}
    msg_classes = {topic: get_message(type_name) for topic, type_name in topic_types.items()}

    first_stamp = None
    stats = {
        robot: {
            "odom_before": 0,
            "odom_after": 0,
            "cmd_before": 0,
            "cmd_after": 0,
            "moving_cmd_before": 0,
            "moving_cmd_after": 0,
            "amcl_before": 0,
            "amcl_after": 0,
            "last_after_stamp": None,
        }
        for robot in TOPICS
    }

    while reader.has_next():
        topic, data, stamp = reader.read_next()
        if topic not in msg_classes:
            continue
        if first_stamp is None:
            first_stamp = stamp
        elapsed = (stamp - first_stamp) / 1e9
        suffix = "after" if elapsed >= fault_time_s else "before"

        msg = deserialize_message(data, msg_classes[topic])
        for robot, topics in TOPICS.items():
            if topic == topics["odom"]:
                stats[robot][f"odom_{suffix}"] += 1
            elif topic == topics["cmd_vel"]:
                stats[robot][f"cmd_{suffix}"] += 1
                if moving_cmd(msg):
                    stats[robot][f"moving_cmd_{suffix}"] += 1
            elif topic == topics["amcl"]:
                stats[robot][f"amcl_{suffix}"] += 1
            else:
                continue

            if suffix == "after":
                stats[robot]["last_after_stamp"] = elapsed

    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bag")
    parser.add_argument("--target-robot", choices=("TB3_1", "TB3_2"), required=True)
    parser.add_argument("--fault-time-s", type=float, required=True)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--repeat", required=True)
    parser.add_argument("--fault-type", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    stats = read_bag(Path(args.bag), args.fault_time_s)
    survivor = "TB3_2" if args.target_robot == "TB3_1" else "TB3_1"
    survivor_stats = stats[survivor]
    survivor_continued = (
        survivor_stats["odom_after"] > 0
        and survivor_stats["cmd_after"] > 0
        and survivor_stats["last_after_stamp"] is not None
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        fieldnames = [
            "run_id",
            "layout",
            "repeat",
            "target_robot",
            "survivor_robot",
            "fault_type",
            "fault_time_s",
            "survivor_continued",
            "survivor_odom_after",
            "survivor_cmd_after",
            "survivor_moving_cmd_after",
            "survivor_amcl_after",
            "survivor_last_after_s",
            "target_odom_after",
            "target_cmd_after",
            "notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "run_id": Path(args.bag).name,
            "layout": args.layout,
            "repeat": args.repeat,
            "target_robot": args.target_robot,
            "survivor_robot": survivor,
            "fault_type": args.fault_type,
            "fault_time_s": f"{args.fault_time_s:.1f}",
            "survivor_continued": str(survivor_continued).lower(),
            "survivor_odom_after": survivor_stats["odom_after"],
            "survivor_cmd_after": survivor_stats["cmd_after"],
            "survivor_moving_cmd_after": survivor_stats["moving_cmd_after"],
            "survivor_amcl_after": survivor_stats["amcl_after"],
            "survivor_last_after_s": "" if survivor_stats["last_after_stamp"] is None else f"{survivor_stats['last_after_stamp']:.3f}",
            "target_odom_after": stats[args.target_robot]["odom_after"],
            "target_cmd_after": stats[args.target_robot]["cmd_after"],
            "notes": "survivor continued after target robot fault" if survivor_continued else "survivor did not show post-fault activity",
        })

    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
