#!/usr/bin/env python3
"""Create temporary Nav2 parameter overlays for inflation radius experiments."""

import argparse
import os
import shutil
from pathlib import Path


def link_tree_contents(source: Path, destination: Path) -> None:
    """Mirror one installed package directory using per-file symlinks."""
    if not source.exists():
        return

    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        os.symlink(item, target, target_is_directory=item.is_dir())


def rewrite_inflation_radius(source: Path, destination: Path, radius: str) -> None:
    lines = source.read_text().splitlines()
    rewritten = []
    for line in lines:
        if "inflation_radius:" in line and line.strip().startswith("inflation_radius:"):
            indent = line[: len(line) - len(line.lstrip())]
            rewritten.append(f"{indent}inflation_radius: {radius}")
        else:
            rewritten.append(line)
    destination.write_text("\n".join(rewritten) + "\n")


def make_dual_overlay(dual_ws: Path, radius: str, output_root: Path) -> Path:
    install_share = dual_ws / "install" / "dual_robot_nav" / "share" / "dual_robot_nav"
    install_lib = dual_ws / "install" / "dual_robot_nav" / "lib" / "dual_robot_nav"
    if not install_share.exists():
        raise FileNotFoundError(f"dual_robot_nav install share not found: {install_share}")

    overlay = output_root / f"dual_inflation_{radius.replace('.', '_')}"
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
            rewrite_inflation_radius(cfg, target, radius)
        elif cfg.is_file():
            shutil.copy2(cfg, target)

    lib.parent.mkdir(parents=True)
    os.symlink(install_lib, lib)
    return overlay


def make_single_params(single_ws: Path, radius: str, output_root: Path) -> Path:
    source = (
        single_ws
        / "install"
        / "single_robot_nav"
        / "share"
        / "single_robot_nav"
        / "config"
        / "nav2_params.yaml"
    )
    if not source.exists():
        raise FileNotFoundError(f"single_robot_nav params not found: {source}")
    out_dir = output_root / "single_robot_nav"
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / f"nav2_params_inflation_{radius.replace('.', '_')}.yaml"
    rewrite_inflation_radius(source, destination, radius)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", required=True, help="Inflation radius, e.g. 0.40")
    parser.add_argument("--dual-ws", default="/home/anaskh007/dual_robot_ws")
    parser.add_argument("--single-ws", default="/home/anaskh007/Anasros2_ws")
    parser.add_argument(
        "--output-root",
        default="/home/anaskh007/dual_robot_ws/fyp_testing/results/params",
    )
    parser.add_argument(
        "--mode",
        choices=("dual", "single", "both"),
        default="both",
        help="Which parameter set to generate.",
    )
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    if args.mode in ("dual", "both"):
        overlay = make_dual_overlay(Path(args.dual_ws), args.radius, output_root)
        print(f"DUAL_OVERLAY={overlay}")
    if args.mode in ("single", "both"):
        params = make_single_params(Path(args.single_ws), args.radius, output_root)
        print(f"SINGLE_PARAMS={params}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
