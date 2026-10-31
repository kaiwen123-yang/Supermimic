"""Compare differentiable FK with MuJoCo for every frame of every real clip.

Produces a compact numerical audit, not a unit-test suite or policy evaluation.
"""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from supermimic.kinematics import ForwardKinematics
from supermimic.robot import load_model


def main():
    start = time.monotonic()
    torch.set_num_threads(1)
    fk = ForwardKinematics(load_model()).float()
    source = ROOT / "data/processed/lafan1_g1_50hz"
    manifest = json.loads((source / "manifest.json").read_text())
    rows = []
    for clip in manifest["clips"]:
        record = np.load(source / (clip["name"] + ".npz"))
        maximum = {key: 0.0 for key in ("body_pos", "body_quat", "body_lin_vel", "body_ang_vel")}
        with torch.no_grad():
            for first in range(0, clip["frames"], 512):
                sl = slice(first, first + 512)
                body = fk(torch.from_numpy(record["qpos"][sl]), torch.from_numpy(record["qvel"][sl]))
                for key, value in body.items():
                    reference = torch.from_numpy(record[key][sl])
                    if key == "body_quat":
                        error = torch.minimum((value - reference).abs().amax(-1), (value + reference).abs().amax(-1)).max()
                    else:
                        error = (value - reference).abs().max()
                    maximum[key] = max(maximum[key], error.item())
        rows.append({"motion": clip["name"], "frames": clip["frames"], "max_absolute_errors": maximum})
        print(clip["name"], maximum, flush=True)
    maxima = {key: max(r["max_absolute_errors"][key] for r in rows) for key in maximum}
    # Float32 rotations near fast motion have larger velocity roundoff than positions.
    passed = maxima["body_pos"] < 2e-5 and maxima["body_quat"] < 2e-5 and max(maxima["body_lin_vel"], maxima["body_ang_vel"]) < 2e-3
    result = {"status": "passed" if passed else "failed", "device": "cpu", "dtype": "float32",
              "source_manifest": "results/lafan1_g1_preparation/motion_manifest.json",
              "all_40_full_clips": len(rows) == 40, "frames": sum(r["frames"] for r in rows),
              "maximum_absolute_errors": maxima, "clips": rows, "wall_seconds": time.monotonic() - start,
              "meaning": "Kinematics and velocity consistency only; not physical feasibility or learned control success"}
    path = ROOT / "results/lafan1_g1_preparation/kinematics.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    if not passed:
        raise RuntimeError(f"Kinematics mismatch: {maxima}")
    print("KINEMATICS_COMPLETE", maxima, flush=True)


if __name__ == "__main__":
    main()
