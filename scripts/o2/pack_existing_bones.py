"""Stream the retained P9 qpos/qvel into the author's existing packed format."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np

from common import CAMPAIGN, CODE_ROOT, now, write_csv, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads((CODE_ROOT / "configs/o2_official_bones_protocol.json").read_text())
    data = protocol["data"]
    output = Path(data["output_directory"])
    if (output / "manifest.json").exists():
        print("O2 packed conversion already completed; keeping original output", flush=True)
        return
    started = time.monotonic()
    original = json.loads(Path(data["source_manifest"]).read_text())
    store = original["reference_store"]
    source = Path(store["directory"])
    offset = store["offset"]
    qpos = np.load(source / "qpos.npy", mmap_mode="r")
    qvel = np.load(source / "qvel.npy", mmap_mode="r")
    names = [j.attrib["name"] for j in ET.parse(args.workspace / "mjlab_research/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml").findall(".//worldbody//joint")]
    order = [original["joint_order"].index(name) for name in names]
    clips = []
    cursor = 0
    for index, row in enumerate(original["clips"]):
        end = cursor + row["frames"]
        clips.append({"official_clip_id": index, "source": "bones", "source_clip_id": index,
                      "name": row["name"], "category": row["category"], "package": row["package"],
                      "frames": row["frames"], "reference_transitions": row["frames"] - 1,
                      "source_store_start": offset + cursor, "source_store_end_exclusive": offset + end,
                      "packed_start": cursor, "packed_end_exclusive": end, "source_path": row["source_path"]})
        cursor = end
    output.mkdir(parents=True, exist_ok=True)
    arrays = {name: np.lib.format.open_memmap(output / name, mode="w+", dtype=np.float32, shape=(cursor, spec["width"]))
              for name, spec in data["output_fields"].items()}
    chunk = data["conversion_chunk_frames"]
    for start in range(0, cursor, chunk):
        end = min(cursor, start + chunk)
        pos, vel = qpos[offset + start:offset + end], qvel[offset + start:offset + end]
        quat, omega = pos[:, 3:7], vel[:, 3:6]
        vector = quat[:, 1:]
        values = {"root_pos_w.npy": pos[:, :3], "root_quat_w.npy": quat,
                  "root_lin_vel_w.npy": vel[:, :3],
                  "root_ang_vel_w.npy": omega + 2 * np.cross(vector, np.cross(vector, omega) + quat[:, :1] * omega),
                  "joint_pos.npy": pos[:, 7:][:, order], "joint_vel.npy": vel[:, 6:][:, order]}
        for name, value in values.items():
            arrays[name][start:end] = value
        if start // chunk % 32 == 0:
            print(f"O2_PACK frames={end}/{cursor}", flush=True)
    for array in arrays.values():
        array.flush()
    np.save(output / "motion_ends.npy", np.asarray([c["packed_end_exclusive"] for c in clips], dtype=np.int64))
    write_json(output / "joint_names.json", names)
    write_json(output / "motion_names.json", [c["name"] for c in clips])
    result = args.workspace / "results" / CAMPAIGN
    parts = []
    for first in range(0, len(clips), 2000):
        name = f"data_index/clips_{first // 2000:04d}.csv"
        write_csv(result / name, clips[first:first + 2000])
        parts.append(name)
    record = {"completed_at": now(), "conversion_seconds": time.monotonic() - started,
              "source_manifest": data["source_manifest"], "source_store": str(source),
              "source_fields": ["qpos.npy", "qvel.npy"], "source_offset": offset,
              "source_end_exclusive": offset + cursor, "dataset": original["dataset"],
              "preprocessing_version": original["preprocessing_version"], "control_hz": original["control_hz"],
              "clip_count": len(clips), "frames": cursor, "reference_transitions": cursor - len(clips),
              "joint_names": names, "root_quaternion_order": "wxyz", "units": "m,radians,seconds",
              "conversion": "O1 joint reorder and root local angular velocity to world; no recenter/resample/filter",
              "output_directory": str(output), "index_parts": parts, "source_id_definition": data["source_id_definition"],
              "official_commit": protocol["source_snapshot"]["official_commit"],
              "research_commit": protocol["source_snapshot"]["research_commit"]}
    write_json(result / "data_conversion.json", record)
    write_json(output / "manifest.json", {**record, "clips": clips})
    print(f"O2_PACK_COMPLETE clips={len(clips)} frames={cursor} seconds={record['conversion_seconds']:.1f}", flush=True)


if __name__ == "__main__":
    main()
