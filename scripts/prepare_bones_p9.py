"""Convert official G1 data in fixed metadata order; freeze40h and finish the library."""
import csv
import json
import math
import os
import subprocess
import sys
import re
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
from p9_results import read, write
RAW = ROOT / "data/raw/bones_seed"
FULL = ROOT / "data/processed/bones_g1_50hz_full_p9"
SUBSET = ROOT / "data/processed/bones_p9_monitor40"
RESULT = ROOT / "results/20261107-p9-critic-full-scale-s0/bones_data"
CONFIG = ROOT / "configs/bones_p9_preprocessing.json"
OLD_FULL = ROOT.parent / "supermimic-p8-stability-scale/data/processed/bones_g1_50hz_full"


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


def name_matches(name, choices):
    normalized = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    matches = []
    for pattern in choices["name_token_patterns"]:
        candidate = normalized
        for exception in choices["project_name_exceptions"].get(pattern, []):
            candidate = candidate.replace(exception, "groundexercise")
        if re.search(r"(?:^|_)(?:"+pattern+r")(?:_|$)", candidate):
            matches.append("token:"+pattern)
    for phrase in choices["name_phrases"]:
        if re.search(r"(?:^|_)"+re.escape(phrase)+r"(?:_|$)", normalized):
            matches.append("phrase:"+phrase)
    return matches


def convert(row):
    name = row["filename"]
    record = {"name": name, "category": row["category"], "package": row["package"],
        "source_path": row["move_g1_path"], "metadata_frames_120hz": int(row["move_duration_frames"])}
    choices = OPTIONS["project_choices_frozen_before_training"]
    matches = name_matches(name, choices)
    if matches:
        return {**record, "accepted": False, "reasons": ["project_name_filter"], "matched_terms": matches}
    reused = "existing" in row
    if reused:
        with np.load(OLD_FULL / (name+".npz")) as z:
            qpos, qvel = z["qpos"], z["qvel"]
        hz = OPTIONS["target_hz"]
        t = np.arange(len(qpos))/hz
        rotations = Rotation.from_quat(qpos[:, [4,5,6,3]])
        source_frames = row["existing"]["source_frames"]
        record.update(source_frames=source_frames, source_duration_s=(source_frames-1)/120)
    else:
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
        record.update(source_frames=len(raw), source_first_frame=float(frames[0]), source_last_frame=float(frames[-1]), source_duration_s=float(source_time[-1]))
    shape = (len(t), len(BODIES))
    if not reused:
        body_pos, body_quat = np.empty((*shape, 3), np.float32), np.empty((*shape, 4), np.float32)
        body_lin, body_ang = np.empty((*shape, 3), np.float32), np.empty((*shape, 3), np.float32)
    min_z, foot_z = np.empty(len(t)), np.empty(len(t))
    velocity = np.empty(6)
    for frame in range(len(t)):
        DATA.qpos[:], DATA.qvel[:] = qpos[frame], qvel[frame]
        mujoco.mj_kinematics(MODEL, DATA)
        if not reused:
            mujoco.mj_comPos(MODEL, DATA)
            mujoco.mj_comVel(MODEL, DATA)
            body_pos[frame], body_quat[frame] = DATA.xpos[BODIES], DATA.xquat[BODIES]
        lowest = DATA.geom_xpos[GEOMS, 2] - RADIUS - HALF_LENGTH * np.abs(DATA.geom_xmat[GEOMS, 8])
        min_z[frame], foot_z[frame] = DATA.xpos[1:, 2].min(), lowest[FEET].min()
        if not reused:
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
    record.update(reused_existing_reference=reused, frames=len(t), duration_s=float(t[-1]),
        minimum_body_origin_z_m=float(min_z.min()), elevated_longest_seconds=elevated_duration,
        floating_longest_seconds=floating_duration, penetration_fraction=penetration_fraction,
        accepted=not reasons, reasons=reasons)
    if not reasons and reused:
        os.link(OLD_FULL / (name+".npz"), FULL / (name+".npz"))
    elif not reasons:
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


def pack_reference_chunk(task):
    directory, shapes, entries = task
    arrays = {key: np.lib.format.open_memmap(Path(directory)/(key+".npy"), mode="r+") for key in shapes}
    for path, offset, frames in entries:
        with np.load(path) as z:
            for key, target in arrays.items():
                target[offset:offset+frames] = z[key]
    for value in arrays.values():
        value.flush()
    return len(entries)


def build_joint_store(full_manifest, options):
    joint = ROOT / "data/processed/bones_full_lafan_p9"
    joint.mkdir(parents=True, exist_ok=False)
    lafan_dir = ROOT / "data/processed/lafan1_g1_50hz"
    lafan = read(lafan_dir / "manifest.json")
    from supermimic.motion import data_definition
    sources = {"lafan": {"directory": str(lafan_dir), "definition": data_definition(lafan)},
        "bones": {"directory": str(FULL), "repo": options["dataset"], "revision": options["revision"],
            "preprocessing_version": options["preprocessing_version"], "manifest": str(FULL / "manifest.json")}}
    entries, clips, offset = [], [], 0
    for source, directory, source_manifest in (("lafan", lafan_dir, lafan), ("bones", FULL, full_manifest)):
        for clip in source_manifest["clips"]:
            clips.append({**clip, "name": source+"__"+clip["name"], "original_name": clip["name"], "source": source})
            entries.append((str(directory / (clip["name"]+".npz")), offset, clip["frames"]))
            offset += clip["frames"]
    shapes = {"qpos": [36], "qvel": [35], "body_pos": [14,3], "body_quat": [14,4],
        "body_lin_vel": [14,3], "body_ang_vel": [14,3]}
    for key, shape in shapes.items():
        array = np.lib.format.open_memmap(joint / (key+".npy"), mode="w+", dtype=np.float32, shape=(offset,*shape))
        del array
    tasks = [(str(joint), shapes, entries[i:i+128]) for i in range(0,len(entries),128)]
    packed = 0
    with ProcessPoolExecutor(max_workers=16) as pool:
        for count in pool.map(pack_reference_chunk, tasks, chunksize=1):
            packed += count
            if packed % 2048 == 0:
                print("REFERENCE_STORE_PACKED", packed, len(entries), flush=True)
    joint_manifest = {**full_manifest, "dataset": {"repo": "lafan1+bones-studio/seed", "revision": "p9-frozen-two-source"},
        "clips": clips, "clip_count": len(clips), "frames_50hz": offset, "sources": sources,
        "resampled_duration_hours": sum((c["frames"]-1)/50 for c in clips)/3600,
        "reference_store": {"directory": str(joint), "offset": 0, "shapes": shapes},
        "environment_source_counts": {"lafan": 1024, "bones": 3072}}
    full_manifest.update(sources={"bones": sources["bones"]},
        reference_store={"directory": str(joint), "offset": sum(c["frames"] for c in lafan["clips"]), "shapes": shapes})
    for clip in full_manifest["clips"]:
        clip["source"] = "bones"
    for path, value in ((joint/"manifest.json", joint_manifest), (FULL/"manifest.json", full_manifest),
                        (RESULT/"full_manifest.json", full_manifest), (RESULT/"joint_manifest.json", joint_manifest)):
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"))+"\n")
    return joint_manifest


def main():
    options = read(CONFIG)
    RESULT.mkdir(parents=True, exist_ok=True)
    FULL.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    with (RAW / options["metadata"]).open() as f:
        metadata = list(csv.DictReader(f))
    old = {c["name"]: c for c in read(OLD_FULL / "manifest.json")["clips"]}
    groups = defaultdict(list)
    for row in metadata:
        if row["filename"] in old:
            row["existing"] = old[row["filename"]]
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
    model = mujoco.MjModel.from_xml_path(str(ROOT / "data/robot/g1.xml"))
    write(RESULT/"filter_definition.json", {"config": options,
        "body_origin_names": [model.body(i).name for i in range(1, model.nbody)],
        "foot_distance": "Minimum exact sphere/capsule surface-to-plane distance over both foot collision geoms; >threshold means both feet above plane.",
        "original_candidates": len(metadata), "old_manifest": str(OLD_FULL/"manifest.json")})
    kept, subset, reasons, overlaps = [], [], Counter(), Counter()
    subset_seconds, name_pass, reused, converted = 0., 0, 0, 0
    shards = RESULT/"filter_records"
    shards.mkdir()
    log = None
    with ProcessPoolExecutor(max_workers=16, initializer=init_worker) as pool:
        pending, cursor, processed = deque(), 0, 0
        while cursor < len(ordered) or pending:
            while cursor < len(ordered) and len(pending) < 64:
                pending.append(pool.submit(convert, ordered[cursor]))
                cursor += 1
            record = pending.popleft().result()
            if processed % 2000 == 0:
                if log is not None:
                    log.close()
                log = (shards/f"part_{processed//2000:04d}.jsonl").open("w", buffering=1)
            log.write(json.dumps(record, ensure_ascii=False, separators=(",", ":"))+"\n")
            processed += 1
            reasons.update(record["reasons"])
            overlaps["+".join(sorted(record["reasons"])) or "accepted"] += 1
            name_pass += "project_name_filter" not in record["reasons"]
            if "reused_existing_reference" in record:
                reused += record["reused_existing_reference"]
                converted += not record["reused_existing_reference"]
            if record["accepted"]:
                kept.append(record)
                if subset_seconds < options["subset_target_hours"]*3600:
                    subset.append(record)
                    subset_seconds += record["duration_s"]
            if processed % 1000 == 0:
                write(RESULT/"preparation.json", {"status": "correcting_all_candidates", "processed_candidates": processed,
                    "candidate_clips": len(ordered), "name_pass": name_pass, "accepted": len(kept),
                    "workers": 16, "reused_existing_npz": reused, "necessary_conversions": converted,
                    "wall_seconds": time.monotonic()-started, "exclusion_reason_counts": dict(reasons)})
                print("P9_BONES_FILTER", processed, len(ordered), len(kept), flush=True)
    log.close()
    full_manifest = manifest(kept, options)
    monitor = manifest(subset, options)
    write(RESULT/"monitor40_manifest.json", monitor)
    stats = {"status": "packing_cpu_reference_store", "candidate_clips": len(ordered), "name_pass": name_pass,
        "physics_pass": len(kept), "accepted": len(kept), "excluded_unique": len(ordered)-len(kept),
        "exclusion_reason_counts": dict(reasons), "reason_intersections": dict(overlaps), "workers": 16,
        "reused_existing_npz": reused, "necessary_conversions": converted,
        "full_hours": full_manifest["resampled_duration_hours"], "frames_50hz": full_manifest["frames_50hz"],
        "monitor40_clips": len(subset), "monitor40_hours": subset_seconds/3600,
        "categories": dict(Counter(c["category"] for c in kept)),
        "name_skill_groups": {g: sum(g in c["name"].lower() for c in kept) for g in ("flip","side_roll","cartwheel","handstand")},
        "filter_wall_seconds": time.monotonic()-started}
    write(RESULT/"preparation.json", stats)
    joint = build_joint_store(full_manifest, options)
    stats.update(status="completed", joint_clips=joint["clip_count"], wall_seconds=time.monotonic()-started,
        complete_reference_storage="CPU read-only mmap; same files shared by training and evaluation", backup_status="awaiting_user_export_not_confirmed")
    write(RESULT/"preparation.json", stats)
    write(shards/"index.json", {"records": processed, "chunk_clips":2000,
        "parts":[f"part_{i:04d}.jsonl" for i in range((processed+1999)//2000)], "reason_counts_overlap":True})
    print("P9_CORRECTED_FULL_LIBRARY_READY", len(kept), stats["full_hours"], flush=True)


if __name__ == "__main__":
    main()

