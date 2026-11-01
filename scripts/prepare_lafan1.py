"""Convert all 40 complete clips and audit actual reference kinematics on CPU.

This does not execute a control policy and is not a tracking-success evaluation.
All source clips, including retargeting violations, remain in the manifest.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from supermimic.robot import JOINTS, TRACKED_BODIES, build_model, joint_arrays


def resample(raw: np.ndarray, source_hz: int = 30, target_hz: int = 50):
    if raw.ndim != 2 or raw.shape[1] != 36 or len(raw) < 3 or not np.isfinite(raw).all():
        raise ValueError(f"Invalid motion array {raw.shape}")
    norms = np.linalg.norm(raw[:, 3:7], axis=1)
    if np.any(norms < 1e-8):
        raise ValueError("Zero reference quaternion")
    source_time = np.arange(len(raw), dtype=np.float64) / source_hz
    n = int(np.floor(source_time[-1] * target_hz + 1e-9)) + 1
    target_time = np.arange(n, dtype=np.float64) / target_hz
    # No extrapolation and no clip truncation to a short prefix.
    rotations = Slerp(source_time, Rotation.from_quat(raw[:, 3:7]))(target_time)
    qpos = np.empty((n, 36), dtype=np.float64)
    for column in list(range(3)) + list(range(7, 36)):
        qpos[:, column] = np.interp(target_time, source_time, raw[:, column])
    quaternions = rotations.as_quat()[:, [3, 0, 1, 2]]
    signs = np.where(np.sum(quaternions[1:] * quaternions[:-1], axis=-1) < 0, -1.0, 1.0)
    quaternions[1:] *= np.cumprod(signs)[:, None]
    qpos[:, 3:7] = quaternions
    qvel = np.empty((n, 35), dtype=np.float64)
    qvel[:, :3] = np.gradient(qpos[:, :3], 1 / target_hz, axis=0, edge_order=2)
    qvel[:, 6:] = np.gradient(qpos[:, 7:], 1 / target_hz, axis=0, edge_order=2)
    left = np.maximum(np.arange(n) - 1, 0)
    right = np.minimum(np.arange(n) + 1, n - 1)
    world_omega = (rotations[right] * rotations[left].inv()).as_rotvec()
    world_omega /= ((right - left) / target_hz)[:, None]
    # MuJoCo free-joint qvel: translation in world, angular velocity in root frame.
    qvel[:, 3:6] = rotations.inv().apply(world_omega)
    return target_time, qpos, qvel, float(np.max(np.abs(norms - 1)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, default=ROOT / "results/lafan1_g1_preparation")
    args = parser.parse_args()
    started = time.monotonic()
    lock = json.loads((ROOT / "configs/sources.lock.json").read_text())
    sources = ROOT / "data/raw/lafan1_g1"
    downloads = json.loads((sources / "download_manifest.json").read_text())
    csvs = [row for row in downloads["files"] if row["path"].endswith(".csv")]
    if len(csvs) != 40 or downloads["revision"] != lock["lafan1"]["revision"]:
        raise RuntimeError("The pinned complete 40-clip download is required")
    model_path = ROOT / "data/robot/g1.xml"
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    body_ids = [model.body(name).id for name in TRACKED_BODIES]
    body_pos = body_quat = body_lin = body_ang = None
    velocity = np.empty(6)
    nominal = joint_arrays()
    output = ROOT / "data/processed/lafan1_g1_50hz"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    lower, upper = model.jnt_range[1:, 0], model.jnt_range[1:, 1]
    soft_mid = (lower + upper) / 2
    soft_half = (upper - lower) * 0.9 / 2
    for row in csvs:
        source = sources / row["path"]
        raw = np.loadtxt(source, delimiter=",")
        t, qpos, qvel, quat_error = resample(raw)
        shape = (len(t), len(body_ids))
        body_pos = np.empty((*shape, 3), dtype=np.float32)
        body_quat = np.empty((*shape, 4), dtype=np.float32)
        body_lin = np.empty((*shape, 3), dtype=np.float32)
        body_ang = np.empty((*shape, 3), dtype=np.float32)
        for frame in range(len(t)):
            data.qpos[:] = qpos[frame]
            data.qvel[:] = qvel[frame]
            mujoco.mj_kinematics(model, data)
            mujoco.mj_comPos(model, data)
            mujoco.mj_comVel(model, data)
            body_pos[frame] = data.xpos[body_ids]
            body_quat[frame] = data.xquat[body_ids]
            for slot, bid in enumerate(body_ids):
                # BODY velocity is centered on the inertial COM; XBODY matches
                # xpos/xquat at the link origin used by the tracking reward.
                mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_XBODY, bid, velocity, 0)
                body_ang[frame, slot] = velocity[:3]
                body_lin[frame, slot] = velocity[3:]
        target = output / (source.stem + ".npz")
        np.savez_compressed(target, fps=np.array(50), time=t,
                            qpos=qpos.astype(np.float32), qvel=qvel.astype(np.float32),
                            body_pos=body_pos, body_quat=body_quat, body_lin_vel=body_lin,
                            body_ang_vel=body_ang, joint_names=np.array(JOINTS), body_names=np.array(TRACKED_BODIES))
        hard = np.maximum(lower - qpos[:, 7:], 0) + np.maximum(qpos[:, 7:] - upper, 0)
        soft = np.maximum(soft_mid - soft_half - qpos[:, 7:], 0) + np.maximum(qpos[:, 7:] - soft_mid - soft_half, 0)
        speed = np.abs(qvel[:, 6:]) > nominal["velocity_reference_limit"]
        records.append({
            "name": source.stem, "source_frames": len(raw), "frames": len(t),
            "source_duration_s": (len(raw) - 1) / 30, "duration_s": float(t[-1]),
            "processed_bytes": target.stat().st_size,
            "max_source_quaternion_norm_error": quat_error,
            "hard_joint_limit_frames": int(np.any(hard > 1e-6, axis=1).sum()),
            "max_hard_joint_limit_violation_rad": float(hard.max()),
            "soft_joint_limit_frames": int(np.any(soft > 0, axis=1).sum()),
            "reference_speed_limit_frames": int(np.any(speed, axis=1).sum()),
            "root_height_range_m": [float(qpos[:, 2].min()), float(qpos[:, 2].max())],
            "foot_origin_min_z_m": float(body_pos[:, [3, 6], 2].min()),
            "root_linear_velocity_fk_max_error": float(np.max(np.abs(body_lin[:, 0] - qvel[:, :3]))),
        })
        print(f"CONVERT {source.stem}: {len(raw)} -> {len(t)} frames, {t[-1]:.2f}s, hard-limit frames={records[-1]['hard_joint_limit_frames']}", flush=True)
    result = {
        "stage": "reference_data_and_robot_preparation", "policy_training_started": False,
        "reference_only_not_control_success": True, "dataset": lock["lafan1"],
        "clips": records, "clip_count": len(records), "source_frames": sum(r["source_frames"] for r in records),
        "frames_50hz": sum(r["frames"] for r in records),
        "source_duration_hours": sum(r["source_duration_s"] for r in records) / 3600,
        "resampled_duration_hours": sum(r["duration_s"] for r in records) / 3600,
        "discarded_clips": [], "clipped_joint_values": False,
        "resampling": "linear XYZ/joints; quaternion SLERP; 50 Hz grid including t=0 and every grid point <= last source time; no extrapolation",
        "velocity": "second-order central XYZ/joints; SO(3) central angular difference, root angular qvel expressed locally",
        "joint_order": JOINTS, "body_order": TRACKED_BODIES,
        "full_clip_evaluation_denominator": "0.1 * (frames - 1); rewards after early failure are zero, never renormalize by survived steps",
        "control_hz": 50, "preprocessing_version": "lafan-g1-linear-slerp-central-xbody-v1",
        "wall_seconds": time.monotonic() - started,
    }
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    record_dir = args.result_dir
    record_dir.mkdir(parents=True, exist_ok=True)
    (record_dir / "motion_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"PREPARATION_COMPLETE clips=40 hours={result['source_duration_hours']:.6f} frames={result['frames_50hz']}", flush=True)


if __name__ == "__main__":
    main()
