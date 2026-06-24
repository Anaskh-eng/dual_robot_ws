#!/usr/bin/env python3
"""Create a temporary dual_robot_nav overlay for RPP/DWB comparison."""

import argparse
import os
import shutil
from pathlib import Path

import yaml


GOAL_POSITION_TOLERANCE_M = 0.30
CONTROLLER_FAILURE_TOLERANCE_S = 1.0


DWB_PARAMS = {
    "plugin": "dwb_core::DWBLocalPlanner",
    "debug_trajectory_details": False,
    "min_vel_x": 0.0,
    "min_vel_y": 0.0,
    "max_vel_x": 0.25,
    "max_vel_y": 0.0,
    "max_vel_theta": 1.8,
    "min_speed_xy": 0.0,
    "max_speed_xy": 0.25,
    "min_speed_theta": 0.0,
    "acc_lim_x": 2.5,
    "acc_lim_y": 0.0,
    "acc_lim_theta": 3.2,
    "decel_lim_x": -2.5,
    "decel_lim_y": 0.0,
    "decel_lim_theta": -3.2,
    "vx_samples": 20,
    "vy_samples": 0,
    "vtheta_samples": 40,
    "sim_time": 2.0,
    "linear_granularity": 0.05,
    "angular_granularity": 0.025,
    "transform_tolerance": 0.2,
    "xy_goal_tolerance": GOAL_POSITION_TOLERANCE_M,
    "trans_stopped_velocity": 0.05,
    "short_circuit_trajectory_evaluation": True,
    "stateful": True,
    "critics": [
        "RotateToGoal",
        "Oscillation",
        "BaseObstacle",
        "GoalAlign",
        "PathAlign",
        "PathDist",
        "GoalDist",
    ],
    "BaseObstacle.scale": 0.02,
    "PathAlign.scale": 32.0,
    "PathAlign.forward_point_distance": 0.1,
    "GoalAlign.scale": 24.0,
    "GoalAlign.forward_point_distance": 0.1,
    "PathDist.scale": 32.0,
    "GoalDist.scale": 24.0,
    "RotateToGoal.scale": 32.0,
    "RotateToGoal.slowing_factor": 5.0,
    "RotateToGoal.lookahead_time": -1.0,
}


def link_tree_contents(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        os.symlink(item, destination / item.name, target_is_directory=item.is_dir())


def set_inflation_radius(data, radius):
    for costmap_name in ("local_costmap", "global_costmap"):
        costmap = data.get(costmap_name, {}).get(costmap_name, {}).get("ros__parameters", {})
        inflation = costmap.get("inflation_layer")
        if isinstance(inflation, dict):
            inflation["inflation_radius"] = radius


def rewrite_params(source, destination, controller, radius):
    with source.open() as handle:
        data = yaml.safe_load(handle)

    controller_params = data["controller_server"]["ros__parameters"]
    # Apply identical completion and patience criteria to both benchmark controllers.
    controller_params["failure_tolerance"] = CONTROLLER_FAILURE_TOLERANCE_S
    controller_params["general_goal_checker"]["xy_goal_tolerance"] = (
        GOAL_POSITION_TOLERANCE_M
    )
    if controller == "dwb":
        controller_params["FollowPath"] = dict(DWB_PARAMS)
    elif controller != "rpp":
        raise ValueError(f"Unsupported controller: {controller}")

    set_inflation_radius(data, radius)
    with destination.open("w") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def make_overlay(dual_ws, controller, radius, output_root):
    install_share = dual_ws / "install" / "dual_robot_nav" / "share" / "dual_robot_nav"
    install_lib = dual_ws / "install" / "dual_robot_nav" / "lib" / "dual_robot_nav"
    if not install_share.exists():
        raise FileNotFoundError(f"dual_robot_nav install share not found: {install_share}")

    radius_label = str(radius).replace(".", "_")
    overlay = output_root / f"dual_controller_{controller}_inflation_{radius_label}"
    share = overlay / "share" / "dual_robot_nav"
    config = share / "config"
    resource = overlay / "share" / "ament_index" / "resource_index" / "packages"
    lib = overlay / "lib" / "dual_robot_nav"

    if overlay.exists():
        shutil.rmtree(overlay)

    resource.mkdir(parents=True)
    (resource / "dual_robot_nav").write_text("")
    share.mkdir(parents=True)
    config.mkdir()

    for name in ("launch", "maps", "worlds", "rviz"):
        link_tree_contents(install_share / name, share / name)

    package_xml = install_share / "package.xml"
    if package_xml.exists():
        os.symlink(package_xml, share / "package.xml")

    for cfg in install_share.joinpath("config").iterdir():
        target = config / cfg.name
        if cfg.name in ("nav2_params_tb3_1.yaml", "nav2_params_tb3_2.yaml"):
            rewrite_params(cfg, target, controller, radius)
        elif cfg.is_file():
            shutil.copy2(cfg, target)

    lib.parent.mkdir(parents=True)
    os.symlink(install_lib, lib)
    return overlay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller", choices=("rpp", "dwb"), required=True)
    parser.add_argument("--inflation-radius", type=float, default=0.40)
    parser.add_argument("--dual-ws", default="/home/anaskh007/dual_robot_ws")
    parser.add_argument(
        "--output-root",
        default="/home/anaskh007/dual_robot_ws/fyp_testing/results/params",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    overlay = make_overlay(
        Path(args.dual_ws),
        args.controller,
        args.inflation_radius,
        output_root,
    )
    print(f"DUAL_OVERLAY={overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
