"""Full frozen BONES subset scoring with bounded batches and online clip scalars."""
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from supermimic.motion import MotionLibrary, checkpoint_data_definition
from supermimic.simulator import G1Simulator
from supermimic.kinematics import ForwardKinematics
from supermimic.networks import Actor, actor_root_position_error
from supermimic.task import observation, reward_and_termination
from supermimic.geometry import quat_apply, quat_inv, quat_mul, quat_to_rotvec, yaw_quat
from supermimic.checkpointing import pin_checkpoint
from p9_metrics import tail_group, write_parts, groups


@torch.no_grad()
def evaluate(checkpoint_path, output, failure_tails, source):
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    cfg = checkpoint["config"]
    training_definition = checkpoint_data_definition(checkpoint)
    evaluation_directory = ROOT / cfg["evaluation_sources"][source]
    motions = MotionLibrary(evaluation_directory, "cuda", "cpu_memmap")
    iteration, actor_updates = checkpoint["iteration"], checkpoint["actor_updates"]
    actor = Actor(cfg["actor_root_position_feedback"]).cuda().eval()
    actor.load_state_dict(checkpoint["actor"])
    del checkpoint
    count = len(motions.names)
    batch = min(1024, count)
    sim = G1Simulator(batch)
    fk = ForwardKinematics(sim.host_model).float().cuda()
    # Frozen manifest order, with independent two-tail quotas.
    order = list(range(count))
    tail_counts = {g:0 for g in ("flip","side_roll","ground_getup_or_roll","other")}
    records, tails = [], []
    state_keys = ("qpos", "qvel", "reference_qpos", "reference_qvel")
    scalar_keys = ("root_position_error_m", "root_xy_error_m", "root_orientation_error_rad", "relative_body_position_error_m", "joint_rmse_rad")
    for first in range(0, count, batch):
        selected = order[first:first+batch]
        n = len(selected)
        clip = torch.tensor(selected + [selected[0]]*(batch-n), device="cuda")
        frame = torch.zeros(batch, dtype=torch.long, device="cuda")
        initial = motions.get(clip, frame)
        sim.reset(initial["qpos"], initial["qvel"])
        previous_action = torch.zeros((batch, 29), device="cuda")
        obs = observation(sim.qpos, sim.qvel, previous_action, sim.q0, sim.context[:, 1:30])
        history = obs[:, None].repeat(1, 10, 1)
        active = torch.arange(batch, device="cuda") < n
        failed = torch.zeros_like(active)
        lengths = motions.lengths[clip]-1
        steps = torch.zeros(batch, dtype=torch.long, device="cuda")
        sums = {key: torch.zeros(batch, dtype=torch.float64, device="cuda") for key in (*scalar_keys, "reward", "tracking", "upright", "heading_error_upright")}
        component_sum = torch.zeros((batch, 8), dtype=torch.float64, device="cuda")
        last_error = torch.zeros(batch, device="cuda")
        reasons = ["completed"] * batch
        # 133 state frames and132 transitions per live environment, at most8 saved candidates.
        ring, candidates = {}, {}
        capture = failure_tails and any(v < 2 for v in tail_counts.values())
        if capture:
            for key, value in {"qpos": sim.qpos, "qvel": sim.qvel, "reference_qpos": initial["qpos"], "reference_qvel": initial["qvel"]}.items():
                ring[key] = np.empty((133, batch, *value.shape[1:]), dtype=np.float32)
                ring[key][0] = value.cpu().numpy()
        tick = 0
        while bool(active.any()):
            if tick % 32 == 0:
                window = motions.window(clip, frame, 43)
            offset = tick % 32
            position_error = actor_root_position_error(sim.qpos, window.get(offset)["qpos"], cfg["actor_root_position_scale_m"])
            action = actor(history, window.goal(offset, goal_frame=cfg["goal_frame"], root_quaternion=sim.qpos[:, 3:7]), position_error)
            qpos, qvel = sim.step(action)
            reference = window.get(offset+1)
            reward, done, metrics = reward_and_termination(fk(qpos, qvel), reference, qpos, action, previous_action, sim.soft_lower, sim.soft_upper)
            invalid = ~(torch.isfinite(qpos).all(-1) & torch.isfinite(qvel).all(-1) & torch.isfinite(reward))
            done |= invalid
            gravity = torch.zeros((batch, 3), device="cuda"); gravity[:, 2] = -1
            robot_gz = quat_apply(quat_inv(qpos[:, 3:7]), gravity)[:, 2]
            ref_gz = quat_apply(quat_inv(reference["qpos"][:, 3:7]), gravity)[:, 2]
            upright = (robot_gz < -2**-.5) & (ref_gz < -2**-.5)
            heading = quat_to_rotvec(quat_mul(yaw_quat(qpos[:, 3:7]), quat_inv(yaw_quat(reference["qpos"][:, 3:7])))).norm(dim=-1)
            values = {"qpos": qpos, "qvel": qvel, "reference_qpos": reference["qpos"], "reference_qvel": reference["qvel"],
                "action": action, "previous_action": previous_action, "reward": torch.where(invalid, torch.zeros_like(reward), reward),
                "reward_components": metrics.pop("components"), **metrics,
                "root_xy_error_m": (qpos[:, :2]-reference["qpos"][:, :2]).norm(dim=-1),
                "joint_rmse_rad": (qpos[:, 7:]-reference["qpos"][:, 7:]).square().mean(-1).sqrt(),
                "heading_error_rad": heading, "upright": upright, "survived": ~done, "invalid": invalid,
                "tracking": ~done & (metrics["root_position_error_m"] <= .3) & (metrics["root_orientation_error_rad"] <= .4)}
            for key in (*scalar_keys, "reward", "tracking", "upright"):
                sums[key].add_(torch.where(active, values[key], 0).double())
            sums["heading_error_upright"].add_(torch.where(active & upright, heading, 0).double())
            component_sum.add_(torch.where(active[:, None], values["reward_components"], 0).double())
            steps.add_(active.long())
            last_error = torch.where(active, values["root_position_error_m"], last_error)
            just_failed = active & done
            if capture:
                for key, value in values.items():
                    array = value.cpu().numpy()
                    if key not in ring:
                        ring[key] = np.empty((133, batch, *array.shape[1:]), dtype=array.dtype)
                    ring[key][(tick+1 if key in state_keys else tick) % 133] = array
            for i in torch.nonzero(just_failed).flatten().tolist():
                reasons[i] = "nonfinite" if invalid[i] else ("root_height" if metrics["root_height_error_m"][i] > .25 else "root_tilt")
                group = tail_group(motions.names[selected[i]])
                group_ids = [j for j in candidates if tail_group(motions.names[selected[j]]) == group]
                quota = 2-tail_counts[group]
                if capture and quota > 0 and (len(group_ids) < quota or i < max(group_ids)):
                    start = max(0, tick+1-132)
                    arrays = {key: value[np.arange(start, tick+2 if key in state_keys else tick+1) % 133, i].copy() for key, value in ring.items()}
                    arrays.update(integer_state_frames=np.arange(start, tick+2), integer_action_frames=np.arange(start, tick+1),
                        context=np.array([1.]+[0.]*32, dtype=np.float32), dt=.02, motion=motions.names[selected[i]], iteration=iteration)
                    candidates[i] = arrays
                    group_ids.append(i)
                    if len(group_ids) > quota:
                        del candidates[max(group_ids)]
            failed |= just_failed
            active &= ~(done | (frame+1 >= lengths))
            frame += 1
            tick += 1
            obs = observation(qpos, qvel, action, sim.q0, sim.context[:, 1:30])
            history = torch.cat((history[:, 1:], obs[:, None]), 1)
            previous_action = action
            ids = torch.nonzero(~active).flatten()
            if len(ids):
                sim.reset(initial["qpos"][ids], initial["qvel"][ids], ids)
        cpu = {key: value.cpu().numpy() for key, value in sums.items()}
        components = component_sum.cpu().numpy()
        for i, motion_id in enumerate(selected):
            total, executed = int(lengths[i]), int(steps[i])
            row = {"source": source, "source_clip_id": motion_id, "motion": motions.names[motion_id], "category": motions.families[motion_id], "failed": bool(failed[i]), "reason": reasons[i],
                "executed_steps": executed, "full_reference_steps": total, "execution_seconds": executed*.02,
                "failure_seconds": executed*.02 if failed[i] else None, "completion_fraction": executed/total,
                "normalized_return": float(cpu["reward"][i])/(.1*total), "tracking_coverage": float(cpu["tracking"][i])/total,
                "reward_component_sums": components[i].tolist(), "upright_steps": int(cpu["upright"][i]),
                "heading_error_upright_rad": float(cpu["heading_error_upright"][i]/cpu["upright"][i]) if cpu["upright"][i] else None,
                "last_frame_root_position_error_m": float(last_error[i]),
                **{"mean_"+key: float(cpu[key][i])/executed for key in scalar_keys}}
            records.append(row)
        for i in sorted(candidates):
            taildir = output / "failure_tails"
            taildir.mkdir(exist_ok=True)
            name = motions.names[selected[i]]
            np.savez_compressed(taildir / (name+".npz"), **candidates[i])
            group = tail_group(name)
            tail_counts[group] += 1
            tails.append({"group": group, "motion": name, "category": motions.families[selected[i]], "npz": name+".npz", "source": "same formal evaluation bounded tail ring"})
        print("BONES_EVALUATED", min(first+batch, count), count, flush=True)
    if failure_tails:
        (output / "failure_tails").mkdir(exist_ok=True)
        (output / "failure_tails/manifest.json").write_text(json.dumps(tails, indent=2)+"\n")
    result = {"status": "evaluated", "method": cfg["method"], "iteration": iteration, "actor_updates": actor_updates,
        "evaluation_source": source, "evaluation_manifest": str(motions.manifest_path),
        "data_definition": {k:v for k,v in motions.data_definition.items() if k != "clips"},
        "training_data_definition": {k:v for k,v in training_definition.items() if k != "clips"},
        "training_manifest": str(ROOT/cfg["data_directory"]/"manifest.json"),
        "training_clip_count": len(training_definition["clips"]), "cross_dataset_evaluation": True,
        "motions": count, "clips": records, "completed_motions": sum(not r["failed"] for r in records),
        "failed_motions": sum(r["failed"] for r in records), "wall_seconds": time.monotonic()-started,
        "evaluation_batch_size": batch, "full_trajectories_saved": False,
        "protocol": {"start_frame": 0, "friction": 1, "observation_noise": False, "domain_randomization": False,
            "training_timeout_applied": False, "normalization": "Per clip sum rewards/(0.1*(N_frames-1)); arithmetic mean over all selected clips"}}
    for key in ("normalized_return", "completion_fraction", "tracking_coverage", "execution_seconds"):
        result["mean_"+key] = sum(r[key] for r in records)/count
    result["categories"] = {name: {"motions": sum(r["category"] == name for r in records),
        "completed": sum(r["category"] == name and not r["failed"] for r in records)} for name in sorted(set(motions.families))}
    monitor = json.loads((ROOT/"results"/cfg["campaign"]/"bones_data/monitor40_manifest.json").read_text())
    result["quality"] = groups(records, {c["name"] for c in monitor["clips"]})
    result["clip_parts"] = write_parts(output, records)
    result.pop("clips")
    result["fields"] = {"reward_component_sums": ["relative_body_position","body_orientation","body_linear_velocity","body_angular_velocity","global_root_position","global_root_orientation","action_difference_penalty","soft_joint_limit_penalty"],
        "quality_means": "equal clip means; mean errors use executed steps within each clip",
        "normalization": "reward/(0.1*(full_reference_frames-1)); failed suffix contributes zero",
        "source_selection": "corrected BONES only; LAFAN evaluated separately",
        "tail_selection": "frozen manifest order within flip/side_roll/ground_getup_or_roll/other, two each; empty slots stay empty"}
    (output / "evaluation.json").write_text(json.dumps(result, indent=2)+"\n")
    print("BONES_FULL_EVALUATION_COMPLETE", count, result["mean_normalized_return"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--failure-tails", action="store_true")
    parser.add_argument("--source", choices=("bones",), required=True)
    args = parser.parse_args()
    output = args.checkpoint.parent / ("evaluation_"+args.checkpoint.stem.split("_")[-1])
    output.mkdir(parents=True, exist_ok=False)
    with pin_checkpoint(args.checkpoint) as path:
        evaluate(path, output, args.failure_tails, args.source)
