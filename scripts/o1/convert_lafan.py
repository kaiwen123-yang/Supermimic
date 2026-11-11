"""Convert the existing 40 clips to the published research MotionLoader fields."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from common import now, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    source = args.workspace / "data/lafan40_existing50hz"
    output = args.workspace / "data/lafan40_official_npz"
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads((source / "manifest.json").read_text())
    xml = args.workspace / "mjlab_research/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml"
    names = [joint.attrib["name"] for joint in ET.parse(xml).findall(".//worldbody//joint")]
    records = []
    for clip_id, row in enumerate(original["clips"]):
        path = source / (row["name"] + ".npz")
        with np.load(path) as data:
            order = [data["joint_names"].tolist().index(name) for name in names]
            qpos, qvel = data["qpos"], data["qvel"]
            quat = qpos[:, 3:7]
            omega = qvel[:, 3:6]
            vector = quat[:, 1:]
            omega_world = omega + 2 * np.cross(vector, np.cross(vector, omega) + quat[:, :1] * omega)
            target = output / (row["name"] + ".npz")
            np.savez_compressed(
                target,
                root_pos_w=qpos[:, :3],
                root_quat_w=quat,
                root_lin_vel_w=qvel[:, :3],
                root_ang_vel_w=omega_world.astype(np.float32),
                joint_pos=qpos[:, 7:][:, order],
                joint_vel=qvel[:, 6:][:, order],
                joint_names=np.asarray(names),
                fps=np.asarray(original["control_hz"]),
            )
        records.append({
            "project_clip_id": clip_id, "official_clip_id": clip_id,
            "name": row["name"], "frames": row["frames"],
            "duration_seconds": row["duration_s"],
            "source": str(path.resolve()), "official_motion_path": str(target),
            "bytes": target.stat().st_size,
        })
        print(f"CONVERT {row['name']} frames={row['frames']}", flush=True)
    write_json(output / "manifest.json", {
        "created_at": now(), "source_manifest": str((source / "manifest.json").resolve()),
        "research_commit": "dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd",
        "clip_count": len(records), "frames": original["frames_50hz"],
        "control_hz": original["control_hz"], "joint_names": names,
        "conversion": "Reuse all original frames; reorder joints by published G1 XML; rotate root angular qvel from root coordinates to world. No resampling, retargeting or clipping.",
        "root_quaternion_order": "wxyz", "clips": records,
    })


if __name__ == "__main__":
    main()
