"""Convert official G1 data in fixed metadata order; freeze40h and finish the library."""
import csv
import json
import math
import os
import subprocess
import sys
import tarfile
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation, Slerp
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from supermimic.robot import JOINTS, TRACKED_BODIES
from p8_results import read, write
RAW = ROOT / "data/raw/bones_seed"
FULL = ROOT / "data/processed/bones_g1_50hz_full"
SUBSET = ROOT / "data/processed/bones_g1_50hz_40h_s0"
RESULT = ROOT / "results/20261106-p8-stability-scale-s0/bones_data"
CONFIG = ROOT / "configs/bones_p8_preprocessing.json"


def init_worker():
    global MODEL, DATA, BODIES, GEOMS, FEET, RADIUS, HALF_LENGTH, OPTIONS
    OPTIONS = read(CONFIG)
    MODEL = mujoco.MjModel.from_xml_path(str(ROOT / "data/robot/g1.xml"))
    DATA = mujoco.MjData(MODEL)
    BODIES = [MODEL.body(name).id for name in TRACKED_BODIES]
    GEOMS = np.array([i for i in range(MODEL.ngeom) if (MODEL.geom(i).name or "").endswith("_collision")])
    FEET = np.array(["_foot" in MODEL.geom(int(i)).name for i in GEOMS])
    RADIUS = MODEL.geom_size[GEOMS, 0]
    HALF_LENGTH = np.where(MODEL.geom_type[GEOMS] == int(mujoco.mjtGeom.mjGEOM_CAPSULE), MODEL.geom_size[GEOMS, 1], 0)


def longest_run(mask):
    edges = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(np.int8)))
    return int((edges[1::2]-edges[::2]).max()) if len(edges) else 0


def convert(row):
    name = row["filename"]
    record = {"name": name, "category": row["category"], "package": row["package"],
        "source_path": row["move_g1_path"], "metadata_frames_120hz": int(row["move_duration_frames"])}
    choices = OPTIONS["project_choices_frozen_before_training"]
    matches = [s for s in choices["excluded_name_substrings"] if s in name.lower()]
    if matches:
        return {**record, "accepted": False, "reasons": ["project_name_filter"], "matched_terms": matches}
    with (RAW / row["move_g1_path"]).open() as f:
        columns = f.readline().strip().split(",")
        raw = np.loadtxt(f, delimiter=",", ndmin=2)
    if len(raw) < 3 or not np.isfinite(raw).all():
        return {**record, "accepted": False, "reasons": ["invalid_source_values_or_too_short"]}
    lookup = {name: i for i, name in enumerate(columns)}
    frames = raw[:, lookup["Frame"]]
    if np.any(np.diff(frames) <= 0):
        return {**record, "accepted": False, "reasons": ["nonincreasing_source_frames"]}
    source_time = (frames-frames[0])/OPTIONS["source_hz"]
    source_xyz = raw[:, [lookup["root_translate"+a] for a in "XYZ"]] * .01
    source_rotation = Rotation.from_euler("xyz", raw[:, [lookup["root_rotate"+a] for a in "XYZ"]], degrees=True)
    source_joints = np.deg2rad(raw[:, [lookup[j+"_dof"] for j in JOINTS]])
    hz = OPTIONS["target_hz"]
    t = np.arange(int(np.floor(source_time[-1]*hz+1e-9))+1)/hz
    if len(t) < 3:
        return {**record, "accepted": False, "reasons": ["too_short_at_control_rate"]}
    rotations = Slerp(source_time, source_rotation)(t)
    qpos = np.empty((len(t), 36))
    for j in range(3):
        qpos[:, j] = np.interp(t, source_time, source_xyz[:, j])
    qpos[:, 3:7] = rotations.as_quat()[:, [3, 0, 1, 2]]
    signs = np.where(np.sum(qpos[1:, 3:7]*qpos[:-1, 3:7], axis=-1) < 0, -1., 1.)
    qpos[1:, 3:7] *= np.cumprod(signs)[:, None]
    for j in range(29):
        qpos[:, 7+j] = np.interp(t, source_time, source_joints[:, j])
    qvel = np.empty((len(t), 35))
    qvel[:, :3] = np.gradient(qpos[:, :3], 1/hz, axis=0, edge_order=2)
    qvel[:, 6:] = np.gradient(qpos[:, 7:], 1/hz, axis=0, edge_order=2)
    left, right = np.maximum(np.arange(len(t))-1, 0), np.minimum(np.arange(len(t))+1, len(t)-1)
    world_omega = (rotations[right]*rotations[left].inv()).as_rotvec()/((right-left)/hz)[:, None]
    qvel[:, 3:6] = rotations.inv().apply(world_omega)
    shape = (len(t), len(BODIES))
    body_pos, body_quat = np.empty((*shape, 3), np.float32), np.empty((*shape, 4), np.float32)
    body_lin, body_ang = np.empty((*shape, 3), np.float32), np.empty((*shape, 3), np.float32)
    min_z, foot_z = np.empty(len(t)), np.empty(len(t))
    velocity = np.empty(6)
    for frame in range(len(t)):
        DATA.qpos[:], DATA.qvel[:] = qpos[frame], qvel[frame]
        mujoco.mj_kinematics(MODEL, DATA)
        mujoco.mj_comPos(MODEL, DATA)
        mujoco.mj_comVel(MODEL, DATA)
        body_pos[frame], body_quat[frame] = DATA.xpos[BODIES], DATA.xquat[BODIES]
        lowest = DATA.geom_xpos[GEOMS, 2] - RADIUS - HALF_LENGTH * np.abs(DATA.geom_xmat[GEOMS, 8])
        min_z[frame], foot_z[frame] = lowest.min(), lowest[FEET].min()
        for slot, bid in enumerate(BODIES):
            mujoco.mj_objectVelocity(MODEL, DATA, mujoco.mjtObj.mjOBJ_XBODY, bid, velocity, 0)
            body_ang[frame, slot], body_lin[frame, slot] = velocity[:3], velocity[3:]
    thresholds = OPTIONS["paper_known_thresholds"]
    upright = rotations.as_matrix()[:, 2, 2] >= math.cos(math.radians(choices["floating_upright_max_tilt_degrees"]))
    stationary = (np.linalg.norm(qvel[:, :3], axis=1) <= choices["floating_root_linear_speed_max_m_s"]) & (np.linalg.norm(qvel[:, 3:6], axis=1) <= choices["floating_root_angular_speed_max_rad_s"])
    floating = (foot_z > thresholds["floating_feet_minimum_distance_m"]) & upright & stationary & (qpos[:, 2] >= choices["floating_standing_root_min_z_m"])
    elevated_duration = max(0, longest_run(min_z > thresholds["elevated_minimum_z_m"])-1)/hz
    floating_duration = max(0, longest_run(floating)-1)/hz
    penetration_fraction = float(np.mean(min_z < thresholds["penetration_fraction_minimum_z_m"]))
    reasons = []
    if elevated_duration >= thresholds["elevated_continuous_seconds"]:
        reasons.append("elevated_support")
    if min_z.min() < thresholds["penetration_any_minimum_z_m"]:
        reasons.append("penetration_any")
    if penetration_fraction > thresholds["penetration_fraction"]:
        reasons.append("penetration_fraction")
    if floating_duration >= thresholds["floating_continuous_seconds"]:
        reasons.append("stationary_upright_floating_feet")
    record.update(source_frames=len(raw), source_first_frame=float(frames[0]), source_last_frame=float(frames[-1]),
        source_duration_s=float(source_time[-1]), frames=len(t), duration_s=float(t[-1]),
        minimum_collision_z_m=float(min_z.min()), elevated_longest_seconds=elevated_duration,
        floating_longest_seconds=floating_duration, penetration_fraction=penetration_fraction,
        accepted=not reasons, reasons=reasons)
    if not reasons:
        np.savez_compressed(FULL / (name+".npz"), qpos=qpos.astype(np.float32), qvel=qvel.astype(np.float32),
            body_pos=body_pos, body_quat=body_quat, body_lin_vel=body_lin, body_ang_vel=body_ang,
            time=t, fps=hz, joint_names=np.array(JOINTS), body_names=np.array(TRACKED_BODIES))
    return record


def manifest(clips, options):
    return {"dataset": {"repo": options["dataset"], "revision": options["revision"]},
        "clips": [{key: c[key] for key in ("name", "category", "package", "frames", "duration_s", "source_path", "source_frames")} for c in clips],
        "clip_count": len(clips), "resampled_duration_hours": sum(c["duration_s"] for c in clips)/3600,
        "frames_50hz": sum(c["frames"] for c in clips), "joint_order": JOINTS, "body_order": TRACKED_BODIES,
        "control_hz": 50, "preprocessing_version": options["preprocessing_version"],
        "preprocessing_config": str(CONFIG.relative_to(ROOT)), "full_clip_evaluation_denominator": "0.1*(frames-1)", "frozen": True}


def main():
    options = read(CONFIG)
    protocol = read(ROOT / "configs/next_stage_stability_scale_protocol.json")
    RESULT.mkdir(parents=True, exist_ok=True)
    FULL.mkdir(parents=True, exist_ok=True)
    SUBSET.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    write(RESULT / "preparation.json", {"status": "extracting", "workers": 16, "started_unix": time.time()})
    with tarfile.open(RAW / "g1.tar.gz", "r|gz") as archive:
        for member in archive:
            archive.extract(member, RAW, filter="data")
    with (RAW / options["metadata"]).open() as f:
        metadata = list(csv.DictReader(f))
    groups = defaultdict(list)
    for row in metadata:
        groups[row["category"]].append(row)
    rng = np.random.default_rng(options["subset_seed"])
    for category in sorted(groups):
        rng.shuffle(groups[category])
    queues = [deque(groups[c]) for c in sorted(groups)]
    ordered = []
    while any(queues):
        for queue in queues:
            if queue:
                ordered.append(queue.popleft())
    kept, subset, reasons = [], [], Counter()
    subset_seconds, frozen = 0., False
    with ProcessPoolExecutor(max_workers=16, initializer=init_worker) as pool, (RESULT / "filter_records.jsonl").open("w", buffering=1) as log:
        pending = deque()
        cursor = 0
        while cursor < len(ordered) or pending:
            while cursor < len(ordered) and len(pending) < 64:
                pending.append(pool.submit(convert, ordered[cursor]))
                cursor += 1
            record = pending.popleft().result()
            log.write(json.dumps(record, ensure_ascii=False)+"\n")
            reasons.update(record["reasons"])
            if record["accepted"]:
                kept.append(record)
                if not frozen:
                    subset.append(record)
                    subset_seconds += record["duration_s"]
                    os.link(FULL / (record["name"]+".npz"), SUBSET / (record["name"]+".npz"))
                    if subset_seconds >= options["subset_target_hours"]*3600:
                        frozen = True
                        frozen_manifest = manifest(subset, options)
                        write(SUBSET / "manifest.json", frozen_manifest)
                        write(RESULT / "subset_manifest.json", frozen_manifest)
                        write(RESULT / "subset_filter_statistics.json", {"processed_candidates": cursor-len(pending),
                            "retained_subset": len(subset), "hours": subset_seconds/3600, "exclusion_reason_counts": dict(reasons),
                            "categories": {c: {"clips": sum(r["category"] == c for r in subset),
                                "hours": sum(r["duration_s"] for r in subset if r["category"] == c)/3600} for c in sorted(groups)},
                            "freeze_elapsed_seconds": time.monotonic()-started})
                        job = protocol["jobs"]["bones40_transfer_h32"]
                        subprocess.run(["tmux", "new-session", "-d", "-s", job["tmux"], "bash "+str(ROOT / "scripts/start_p8_bones_when_ready.sh")], check=True)
                        subprocess.run(["tmux", "set-option", "-t", job["tmux"], "remain-on-exit", "on"], check=True)
                        print("BONES40_FROZEN_AND_TRANSFER_DISPATCHED", len(subset), subset_seconds/3600, flush=True)
            processed = cursor-len(pending)
            if processed % 100 == 0:
                write(RESULT / "preparation.json", {"status": "converting_full_library" if frozen else "building_fixed40h_subset",
                    "processed_candidates": processed, "candidate_clips": len(ordered), "accepted": len(kept),
                    "subset_frozen": frozen, "subset_hours": subset_seconds/3600, "workers": 16,
                    "wall_seconds": time.monotonic()-started, "exclusion_reason_counts": dict(reasons)})
                print("BONES_CONVERT", processed, len(ordered), len(kept), subset_seconds/3600, flush=True)
    full_manifest = manifest(kept, options)
    write(FULL / "manifest.json", full_manifest)
    write(RESULT / "full_manifest.json", full_manifest)
    write(RESULT / "preparation.json", {"status": "completed", "subset_frozen": frozen, "workers": 16,
        "candidate_clips": len(ordered), "accepted": len(kept), "excluded": len(ordered)-len(kept),
        "exclusion_reason_counts": dict(reasons), "full_hours": full_manifest["resampled_duration_hours"],
        "subset_hours": subset_seconds/3600, "wall_seconds": time.monotonic()-started})
    subprocess.run([sys.executable, "-u", str(ROOT / "scripts/publish_bones_data.py"), "full"], check=True, cwd=ROOT)
    print("BONES_PREPARATION_COMPLETE", len(kept), full_manifest["resampled_duration_hours"], flush=True)


if __name__ == "__main__":
    main()
