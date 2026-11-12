"""One loaded official library, fixed environments, all actual O2 checkpoints."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import fcntl
import json
from pathlib import Path
import time

import torch
import supermimic.tasks  # noqa: F401
from mjlab.tasks.registry import load_env_cfg
from mjlab.utils.lab_api.math import quat_error_magnitude
from supermimic.runners.run_config import load_runner_cfg
from supermimic.runners.supermimic_runner import build_actor, build_world_model
from supermimic.scripts.train_utils import create_env, setup_device
from supermimic.tasks.task_spec import build_actor_obs_td

from common import CAMPAIGN, RUN_NAME, TASK, NODE_ORDER, PUBLICATION_LOCK, QUALITY, hardware, now, write_csv, write_json
from evidence import FailureWindows
from metrics import aggregate, compare_nodes, groups, load_scores, read_rows, write_score_parts
from publish_results import refresh_and_publish


def reset_batch(base, motion, clips, batch_size, device):
    base.reset()
    ids = torch.arange(batch_size, device=device)
    starts = [c["packed_start"] for c in clips]
    starts += [starts[0]] * (batch_size - len(starts))
    frames = torch.tensor(starts, dtype=torch.long, device=device)
    motion.set_time_steps(ids, frames)
    loader = motion.motion
    motion._write_reference_state_to_sim(ids, loader.root_pos_w[frames] + base.scene.env_origins[ids],
        loader.root_quat_w[frames], loader.root_lin_vel_w[frames], loader.root_ang_vel_w[frames],
        loader.joint_pos[frames], loader.joint_vel[frames])
    base.scene.write_data_to_sim()
    base.sim.forward()
    motion.update_relative_body_poses()
    base.sim.sense()
    obs = base.observation_manager.compute(update_history=True)
    base.obs_buf = obs
    return obs


@torch.inference_mode()
def score_batch(base, motion, wm, actor, runner_cfg, cfg, clips, batch_size, device, evidence_dir):
    # The preceding batch creates sensor-history inference tensors; reset them in the same mode.
    count = len(clips)
    obs = reset_batch(base, motion, clips, batch_size, device)
    ref_steps = torch.tensor([c["frames"] - 1 for c in clips] + [0] * (batch_size - count), device=device)
    active = torch.arange(batch_size, device=device) < count
    failed = torch.zeros_like(active)
    steps = torch.zeros(batch_size, dtype=torch.long, device=device)
    rewards_sum = torch.zeros(batch_size, dtype=torch.float64, device=device)
    reward_terms = list(base.reward_manager.active_terms)
    term_sum = torch.zeros(batch_size, len(reward_terms), dtype=torch.float64, device=device)
    hard_names = [name for name, term in cfg.terminations.items() if not term.time_out]
    reasons = torch.zeros(batch_size, len(hard_names), dtype=torch.bool, device=device)
    quality_sum = torch.zeros(batch_size, len(QUALITY), dtype=torch.float64, device=device)
    history = obs["actor"].unsqueeze(1).repeat(1, runner_cfg.history_length, 1)
    max_step_reward = base.step_dt * sum(t.weight for t in cfg.rewards.values() if t.weight > 0)
    windows = None
    if evidence_dir is not None:
        raw_context = torch.cat([spec.read(base) for spec in wm.sim_context.specs], dim=-1).clone()
        windows = FailureWindows(evidence_dir, batch_size, obs["full_state"], motion, raw_context, base.scene.env_origins)
    with torch.inference_mode():
        for step in range(max(c["frames"] - 1 for c in clips)):
            aux = wm.representation.extract_aux_state(obs["full_state"])
            _, goal = wm.representation.compute_wm_goal(motion.motion, motion.time_steps, aux)
            action = actor(build_actor_obs_td({"motion": goal}, history))
            obs, rewards, terminated, truncated, _ = base.step(action)
            # Active is the pre-step mask: includes the first hard-failure transition.
            rewards_sum += torch.where(active, rewards.double(), 0)
            term_sum += torch.where(active[:, None], base.reward_manager.term_rewards.double(), 0)
            delta = motion.robot_anchor_pos_w - motion.anchor_pos_w
            quality = torch.stack([torch.linalg.vector_norm(delta, dim=-1),
                torch.linalg.vector_norm(delta[:, :2], dim=-1), delta[:, 2].abs(),
                quat_error_magnitude(motion.robot_anchor_quat_w, motion.anchor_quat_w),
                torch.linalg.vector_norm(motion.robot_body_pos_w - motion.body_pos_relative_w, dim=-1).mean(-1),
                quat_error_magnitude(motion.robot_body_quat_w, motion.body_quat_relative_w).mean(-1)], dim=-1)
            quality_sum += torch.where(active[:, None], quality.double(), 0)
            steps += active.long()
            new_failures = active & terminated
            failed |= new_failures
            for index, name in enumerate(hard_names):
                reasons[:, index] |= active & base.termination_manager.get_term(name)
            if windows is not None:
                windows.step(step + 1, obs["full_state"], action, rewards, new_failures, clips, reasons, hard_names)
            active &= ~(terminated | truncated | (steps >= ref_steps))
            if not bool(active.any()):
                break
            # Manual-reset obligation applies to every done row, including padding.
            reset_ids = (terminated | truncated).nonzero(as_tuple=False).squeeze(-1)
            if reset_ids.numel():
                obs, _ = base.reset(env_ids=reset_ids)
            history = torch.cat([history[:, 1:], obs["actor"].unsqueeze(1)], dim=1)
    steps, failed, rewards_sum, term_sum, quality_sum, reasons = (
        x[:count].cpu().tolist() for x in (steps, failed, rewards_sum, term_sum, quality_sum, reasons))
    rows = []
    for i, clip in enumerate(clips):
        n = clip["frames"] - 1
        row = {"clip_id": clip["official_clip_id"], "source_clip_id": clip["source_clip_id"],
               "source": clip["source"], "name": clip["name"], "category": clip["category"], "package": clip["package"],
               "reference_frames": clip["frames"], "reference_transitions": n, "executed_transitions": steps[i],
               "reward_sum": rewards_sum[i], "max_step_reward": max_step_reward,
               "normalization_denominator": max_step_reward * n, "normalized_return": rewards_sum[i] / (max_step_reward * n),
               "completion_fraction": steps[i] / n, "hard_failure": failed[i], "completed": steps[i] == n and not failed[i],
               "termination_reason": ";".join(name for j, name in enumerate(hard_names) if reasons[i][j]) or "natural_end"}
        row.update({name: quality_sum[i][j] / steps[i] for j, name in enumerate(QUALITY)})
        row.update({f"reward_{name}": term_sum[i][j] for j, name in enumerate(reward_terms)})
        rows.append(row)
    return rows


def evaluate(workspace, source):
    worker_started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(0)
    device = setup_device("cuda:0")
    result_dir = workspace / "results" / CAMPAIGN
    run_dir = workspace / "outputs" / RUN_NAME
    nodes = json.loads((run_dir / "nodes.json").read_text())
    labels = [n for n in NODE_ORDER if n in nodes]
    manifest = json.loads((workspace / ("data/bones130394_official_packed/manifest.json" if source == "bones_full"
                                        else "data/lafan40_official_npz/manifest.json")).read_text())
    clips = manifest["clips"]
    batch_size = 4096 if source == "bones_full" else 40
    if source != "bones_full":
        offset = 0
        for i, c in enumerate(clips):
            c.update(source_clip_id=i, source="lafan", packed_start=offset,
                     category=c["name"].split("_")[0].rstrip("0123456789"), package="LAFAN1")
            offset += c["frames"]
    ordered = sorted(clips, key=lambda c: (c["frames"] - 1, c["source_clip_id"]))
    cfg = load_env_cfg(TASK, play=True)
    cfg.seed = 0
    cfg.auto_reset = False
    cfg.terminations.pop("time_out")
    cfg.events["foot_friction"].params["ranges"] = (1.0, 1.0)
    cfg.events["base_com"].params["ranges"] = {0: (0.0, 0.0), 1: (0.0, 0.0), 2: (0.0, 0.0)}
    cfg.events["encoder_bias"].params["bias_range"] = (0.0, 0.0)
    for group in cfg.observations.values():
        group.enable_corruption = False
    motion_cfg = cfg.commands["motion"]
    motion_cfg.motion_file = (str(workspace / "data/bones130394_official_packed") if source == "bones_full"
                              else [c["official_motion_path"] for c in clips])
    motion_cfg.sampling_mode = "start"
    motion_cfg.pose_range = {}
    motion_cfg.velocity_range = {}
    motion_cfg.joint_position_range = (0.0, 0.0)
    write_json(result_dir / "evaluation_execution.json", {"phase": source, "worker_started_at": now(),
               "num_envs": batch_size, "total_clips": len(clips), "actual_nodes": labels})
    env = create_env(cfg, batch_size, device)
    base = env.unwrapped
    motion = base.command_manager.get_term("motion")
    payload = torch.load(nodes[labels[0]]["checkpoint"], map_location=device, weights_only=False)
    runner_cfg = load_runner_cfg({"runner_cfg": payload["runner_cfg"]})
    wm = build_world_model(runner_cfg, env, device)
    actor = build_actor(runner_cfg, wm, device)
    del payload
    write_json(result_dir / "resources" / f"{source}_loaded.json", hardware())
    for label in labels:
        output = result_dir / "milestones" / label / source
        if (output / "evaluation.json").exists():
            print(f"O2_KEEP_EXISTING_SCORE {source} {label}", flush=True)
            continue
        started = time.monotonic()
        payload = torch.load(nodes[label]["checkpoint"], map_location=device, weights_only=False)
        wm.load_bundle(payload["world_model"])
        wm.dynamics.eval()
        actor.load_state_dict(payload["actor"])
        actor.eval()
        metadata = payload["metadata"]
        del payload
        write_json(output / "evaluation_config.json", {"env_cfg": asdict(base.cfg), "runner_cfg": asdict(runner_cfg),
            "reference_transition_count": "frames - 1", "batch_size": batch_size, "batch_order": "(frames-1,source_clip_id)",
            "quality_alignment": "O1 post-step refreshed state / advanced reference; native reward/termination timing unchanged",
            "completion_definition": "N-1 physical transitions without hard failure; natural_end label need not imply native motion_end flag",
            "normalizer": "same checkpoint, loaded and frozen", "inactive_padding": "excluded from all scores"})
        if label == "final" and source == "bones_full":
            write_json(output / "failure_windows_schema.json", {
                "source": "same final formal BONES evaluation; no additional physics or WM calls",
                "robot_state": "root_pos(3; env origin already subtracted),root_quat_wxyz(4),joint_pos(29),root_lin_vel_w(3),root_ang_vel_w(3),joint_vel(29)",
                "reference_state": "root_pos_w(3),root_quat_w_wxyz(4),root_lin_vel_w(3),root_ang_vel_w(3),joint_pos(29),joint_vel(29)",
                "actual_context": [{"name": spec.name, "width": spec.dim} for spec in wm.sim_context.specs],
                "context_values": "raw environment values (un-normalized); COM is actual body_ipos, not offset from baseline",
                "env_origin": "environment world origin; root_pos in robot_state has already subtracted it",
                "state_alignment": "initial state and each returned post-step state; references at corresponding advanced frame",
                "reward_alignment": "native environment reward timing retained",
                "window": "k=min(32,transitions before and including first hard failure); k+1 states, k actions/rewards; no padding"})
        batches = run_dir / "score_batches" / source / label
        rows = []
        for index, first in enumerate(range(0, len(ordered), batch_size)):
            batch_file = batches / f"batch_{index:03d}.csv"
            if batch_file.exists():
                batch_rows = read_rows(batch_file)
            else:
                batch_rows = score_batch(base, motion, wm, actor, runner_cfg, cfg,
                    ordered[first:first + batch_size], batch_size, device,
                    output / "failure_windows" if label == "final" and source == "bones_full" else None)
                write_csv(batch_file, batch_rows)
            rows.extend(batch_rows)
            write_json(output / "evaluation_progress.json", {"status": "evaluating", "at": now(), "completed_batches": index + 1,
                "scored_clips": len(rows), "total_clips": len(clips), "all_library_score_available": False})
            print(f"O2_EVALUATE {source} {label} batch={index+1} clips={len(rows)}/{len(clips)}", flush=True)
        index = write_score_parts(output, rows, source)
        result = {**aggregate(rows), "groups": groups(rows, source), "source": source, "label": label,
                  "checkpoint": nodes[label]["checkpoint"], "checkpoint_metadata": metadata,
                  "evaluated_at": now(), "evaluation_seconds_this_process": time.monotonic() - started,
                  "per_clip_index": index, "all_library_score_available": True,
                  "return_over_SONIC_0p90": aggregate(rows)["mean_normalized_return"] > 0.90 if source == "bones_full" else None,
                  "interpretation": "official algorithm on project 130394 BONES; paper membership not identical" if source == "bones_full"
                                    else "BONES-only fresh policy cross-library LAFAN evaluation; not O1 forgetting or proven disjoint generalization"}
        for previous_label in labels[:labels.index(label)]:
            previous = result_dir / "milestones" / previous_label / source
            comparison_dir = output / f"versus_{previous_label}"
            write_json(comparison_dir / "comparison.json", compare_nodes(load_scores(previous), rows, comparison_dir))
        write_json(output / "evaluation.json", result)
        write_json(output / "evaluation_progress.json", {"status": "completed", "at": now(), "scored_clips": len(rows),
                                                       "all_library_score_available": True})
        current_nodes = json.loads((run_dir / "nodes.json").read_text())
        completed_sources = [s for s in ("bones_full", "lafan40_cross_library")
                             if (result_dir / "milestones" / label / s / "evaluation.json").exists()]
        current_nodes[label]["completed_evaluation_sources"] = completed_sources
        current_nodes[label]["evaluation_status"] = "completed" if len(completed_sources) == 2 else "partially_completed"
        write_json(run_dir / "nodes.json", current_nodes)
        refresh_and_publish(workspace, f"{source}-{label}")
    env.close()
    worker_record = {"status": "completed", "at": now(), "worker_seconds": time.monotonic() - worker_started,
                     "timing_scope": "library initialization, all remaining nodes and their lightweight publication in this worker"}
    write_json(run_dir / f"{source}_worker.json", worker_record)
    write_json(result_dir / f"{source}_worker.json", worker_record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source", choices=("bones_full", "lafan40_cross_library"), required=True)
    args = parser.parse_args()
    with PUBLICATION_LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        evaluate(args.workspace, args.source)
