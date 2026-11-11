"""Index the existing D57 inputs for O1; do not load or convert motion arrays.

Run with the existing system Python. This script needs only the standard library
and does not import either implementation or modify the source datasets.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path("/root/autodl-tmp/robot-repro")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    lafan_dir = ROOT / "supermimic-p4-c0/data/processed/lafan1_g1_50hz"
    manifest_path = lafan_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    records = []
    for clip_id, clip in enumerate(manifest["clips"]):
        path = lafan_dir / (clip["name"] + ".npz")
        records.append({
            "project_clip_id": clip_id,
            "name": clip["name"],
            "source_frames_30hz": clip["source_frames"],
            "frames_50hz": clip["frames"],
            "duration_seconds": clip["duration_s"],
            "existing_processed_path": str(path),
            "existing_processed_bytes": path.stat().st_size,
            "official_clip_id": None,
            "official_motion_path": None,
        })
    with (args.output_dir / "lafan40_index.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    joint_dir = ROOT / "supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9"
    joint = json.loads((joint_dir / "manifest.json").read_text())
    bones_path = Path(joint["sources"]["bones"]["manifest"])
    bones = json.loads(bones_path.read_text())
    arrays = []
    for field in joint["reference_store"]["shapes"]:
        path = joint_dir / (field + ".npy")
        arrays.append({"field": field, "path": str(path.resolve()), "bytes": path.stat().st_size})

    result = {
        "recorded_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "purpose": "existing_input_index_not_official_loader_conversion",
        "lafan": {
            "manifest_path": str(manifest_path),
            "workspace_reference": str(ROOT / "supermimic-official-workspace/data/lafan40_existing50hz"),
            "dataset": manifest["dataset"],
            "clip_count": manifest["clip_count"],
            "indexed_files": len(records),
            "frames_50hz": manifest["frames_50hz"],
            "resampled_duration_hours": manifest["resampled_duration_hours"],
            "source_duration_hours": manifest["source_duration_hours"],
            "processed_file_bytes": sum(row["existing_processed_bytes"] for row in records),
            "control_hz": manifest["control_hz"],
            "joint_order": manifest["joint_order"],
            "body_order": manifest["body_order"],
            "preprocessing_version": manifest["preprocessing_version"],
            "resampling": manifest["resampling"],
            "velocity": manifest["velocity"],
            "index": "lafan40_index.csv",
            "official_loader_compatibility": "unresolved_missing_mjlab_research",
        },
        "bones_preserved_reference": {
            "bones_manifest_path": str(bones_path),
            "bones_clip_count": bones["clip_count"],
            "bones_duration_hours": bones["resampled_duration_hours"],
            "joint_manifest_path": str(joint_dir / "manifest.json"),
            "joint_clip_count_including_lafan": joint["clip_count"],
            "joint_frames_50hz": joint["frames_50hz"],
            "source": joint["sources"]["bones"],
            "reference_arrays": arrays,
            "paper_bones_clip_count": 129514,
            "paper_membership_alignment": "unresolved_no_deletions_to_match_count",
            "o1_bones_training_started": False,
        },
        "inspection": "existing JSON manifests and file metadata only; no array load, conversion, hash or model execution",
    }
    (args.output_dir / "data_inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"indexed_lafan_files": len(records), "lafan_bytes": result["lafan"]["processed_file_bytes"], "bones_clip_count": bones["clip_count"], "output_dir": str(args.output_dir)}))


if __name__ == "__main__":
    main()
