"""Score every LAFAN40 clip in the published research environment."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
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

from common import TASK, now, write_json


def evaluate(workspace: Path, checkpoint: Path, output: Path) -> dict:
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(0)
    device = setup_device("cuda:0")
    payload = torch.load(checkpoint, map_location=device, weights_only=False)
    runner_cfg = load_runner_cfg({"runner_cfg": payload["runner_cfg"]})
    manifest = json.loads((workspace / "data/lafan40_official_npz/manifest.json").read_text())
    clips = manifest["clips"]
    cfg = load_env_cfg(TASK, play=True)
    cfg.seed = 0
    cfg.auto_reset = False
    cfg.terminations.pop("time_out")
    friction = cfg.events["foot_friction"]
    friction.params["ranges"] = (1.0, 1.0)
    cfg.events["base_com"].params["ranges"] = {0: (0.0, 0.0), 1: (0.0, 0.0), 2: (0.0, 0.0)}
    cfg.events["encoder_bias"].params["bias_range"] = (0.0, 0.0)
    for group in cfg.observations.values():
        group.enable_corruption = False
    motion_cfg = cfg.commands["motion"]
    motion_cfg.motion_file = [clip["official_motion_path"] for clip in clips]
    motion_cfg.sampling_mode = "start"
    motion_cfg.pose_range = {}
    motion_cfg.velocity_range = {}
    motion_cfg.joint_position_range = (0.0, 0.0)
    env = create_env(cfg, len(clips), device)
    base = env.unwrapped
    wm = build_world_model(runner_cfg, env, device)
    wm.load_bundle(payload["world_model"])
    wm.dynamics.eval()
    actor = build_actor(runner_cfg, wm, device)
    actor.load_state_dict(payload["actor"])
    actor.eval()
    motion = base.command_manager.get_term("motion")
    starts = [0]
    for clip in clips[:-1]:
        starts.append(starts[-1] + clip["frames"])
    base.reset(seed=0)
    for index, frame in enumerate(starts):
        motion.reset_to_frame(torch.tensor([index], device=device), frame)
    base.scene.write_data_to_sim()
    base.sim.forward()
    motion.update_relative_body_poses()
    base.sim.sense()
    obs = base.observation_manager.compute(update_history=True)
    base.obs_buf = obs
    count = len(clips)
    ref_steps = torch.tensor([clip["frames"] - 1 for clip in clips], device=device)
    active = torch.ones(count, dtype=torch.bool, device=device)
    failed = torch.zeros_like(active)
    steps = torch.zeros(count, dtype=torch.long, device=device)
    reward_sum = torch.zeros(count, dtype=torch.float64, device=device)
    reward_terms = list(base.reward_manager.active_terms)
    term_sum = torch.zeros(count, len(reward_terms), dtype=torch.float64, device=device)
    hard_names = [name for name, term in cfg.terminations.items() if not term.time_out]
    reasons = torch.zeros(count, len(hard_names), dtype=torch.bool, device=device)
    quality_names = ["root_position_error_m", "root_xy_error_m", "root_z_absolute_error_m",
                     "root_orientation_error_rad", "relative_body_position_error_m", "relative_body_orientation_error_rad"]
    quality_sum = torch.zeros(count, len(quality_names), dtype=torch.float64, device=device)
    history = obs["actor"].unsqueeze(1).repeat(1, runner_cfg.history_length, 1)
    max_step_reward = base.step_dt * sum(term.weight for term in cfg.rewards.values() if term.weight > 0)
    write_json(output / "evaluation_config.json", {"env_cfg": asdict(base.cfg), "runner_cfg": asdict(runner_cfg),
               "max_step_reward": max_step_reward, "reference_transition_count": "frames - 1",
               "quality_alignment": "post-step robot state and advanced reference; original environment reward/termination timing retained"})
    with torch.inference_mode():
        for step in range(max(clip["frames"] - 1 for clip in clips)):
            aux = wm.representation.extract_aux_state(obs["full_state"])
            _, goal = wm.representation.compute_wm_goal(motion.motion, motion.time_steps, aux)
            action = actor(build_actor_obs_td({"motion": goal}, history))
            obs, rewards, terminated, truncated, _ = base.step(action)
            reward_sum += rewards.double() * active
            term_sum += base.reward_manager.term_rewards.double() * active[:, None]
            delta = motion.robot_anchor_pos_w - motion.anchor_pos_w
            quality = torch.stack([
                torch.linalg.vector_norm(delta, dim=-1),
                torch.linalg.vector_norm(delta[:, :2], dim=-1), delta[:, 2].abs(),
                quat_error_magnitude(motion.robot_anchor_quat_w, motion.anchor_quat_w),
                torch.linalg.vector_norm(motion.robot_body_pos_w - motion.body_pos_relative_w, dim=-1).mean(-1),
                quat_error_magnitude(motion.robot_body_quat_w, motion.body_quat_relative_w).mean(-1),
            ], dim=-1)
            quality_sum += quality.double() * active[:, None]
            steps += active.long()
            failed |= active & terminated
            for index, name in enumerate(hard_names):
                reasons[:, index] |= active & base.termination_manager.get_term(name)
            active &= ~(terminated | truncated | (steps >= ref_steps))
            if not bool(active.any()):
                break
            reset_ids = (terminated | truncated).nonzero(as_tuple=False).squeeze(-1)
            if reset_ids.numel():
                obs, _ = base.reset(env_ids=reset_ids)
            history = torch.cat([history[:, 1:], obs["actor"].unsqueeze(1)], dim=1)
            if step % 1000 == 0:
                print(f"O1_EVALUATE step={step + 1} active={int(active.sum())}", flush=True)
    rows = []
    for index, clip in enumerate(clips):
        executed = int(steps[index])
        denominator = max_step_reward * (clip["frames"] - 1)
        row = {"clip_id": index, "name": clip["name"], "reference_frames": clip["frames"],
               "reference_transitions": clip["frames"] - 1, "executed_transitions": executed,
               "reward_sum": float(reward_sum[index]), "max_step_reward": max_step_reward,
               "normalization_denominator": denominator, "normalized_return": float(reward_sum[index]) / denominator,
               "completion_fraction": executed / (clip["frames"] - 1), "hard_failure": bool(failed[index]),
               "completed": executed == clip["frames"] - 1 and not bool(failed[index]),
               "termination_reason": ";".join(name for j, name in enumerate(hard_names) if bool(reasons[index, j])) or "natural_end"}
        row.update({name: float(quality_sum[index, j]) / executed for j, name in enumerate(quality_names)})
        row.update({f"reward_{name}": float(term_sum[index, j]) for j, name in enumerate(reward_terms)})
        rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "per_clip.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {"checkpoint": str(checkpoint), "checkpoint_metadata": payload["metadata"], "evaluated_at": now(),
              "clip_count": count, "completed": sum(row["completed"] for row in rows),
              "failed": sum(not row["completed"] for row in rows),
              "mean_normalized_return": sum(row["normalized_return"] for row in rows) / count,
              "mean_completion_fraction": sum(row["completion_fraction"] for row in rows) / count,
              "completed_clip_names": [row["name"] for row in rows if row["completed"]],
              "per_clip_file": "per_clip.csv", "evaluation_seconds": time.monotonic() - started,
              "protocol": "all 40 from frame 0, deterministic actor, friction 1, no DR/noise, official hard failure or full natural duration, mean of per-clip full-duration-normalized returns"}
    write_json(output / "evaluation.json", result)
    env.close()
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.workspace, args.checkpoint, args.output)
