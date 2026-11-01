"""Matched real/model rollouts to distinguish dynamics error from termination bias.

This is a 32-step model diagnostic at three fixed starts in each of the 40 real
motions. It supplements, and never replaces, complete-motion policy evaluation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from supermimic.checkpointing import pin_checkpoint
from supermimic.geometry import quat_mul, quat_inv, quat_to_rotvec
from supermimic.motion import MotionLibrary
from supermimic.networks import Actor, WorldModel, state_prediction_error
from supermimic.simulator import G1Simulator
from supermimic.task import observation


def hard_failure(state, reference):
    height = (state[:, 2] - reference[:, 2]).abs() > 0.25
    tilt = 2 * (state[:, 4:6].square().sum(-1) - reference[:, 4:6].square().sum(-1)).abs() > 0.8
    return height | tilt


def errors(prediction, truth, mask):
    if not bool(mask.any()):
        return {"samples": 0}
    p, t = prediction[mask], truth[mask]
    rotation = quat_to_rotvec(quat_mul(p[:, 3:7], quat_inv(t[:, 3:7])))
    return {"samples": int(mask.sum()),
            "root_position_rmse_m": float((p[:, :3] - t[:, :3]).square().sum(-1).mean().sqrt()),
            "root_orientation_rmse_rad": float(rotation.square().sum(-1).mean().sqrt()),
            "joint_position_rmse_rad": float((p[:, 7:36] - t[:, 7:36]).square().mean().sqrt()),
            "root_velocity_rmse_m_per_s": float((p[:, 36:39] - t[:, 36:39]).square().sum(-1).mean().sqrt()),
            "normalized_state_mse": float(state_prediction_error(p, t).mean())}


@torch.no_grad()
def diagnose(checkpoint_path, output_dir, output_path=None, termination_mode=None, compare_termination=False):
    torch.set_num_threads(1)
    started = time.monotonic()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if "world_model" not in checkpoint:
        raise ValueError("This diagnostic requires a SuperMimic world model")
    motions = MotionLibrary(ROOT / "data/processed/lafan1_g1_50hz", "cuda")
    if checkpoint["dataset_manifest_sha256"] != motions.manifest_hash:
        raise ValueError("Dataset changed")
    actor, world = Actor().cuda().eval(), WorldModel().cuda().eval()
    actor.load_state_dict(checkpoint["actor"])
    world.load_state_dict(checkpoint["world_model"])
    mode = termination_mode or checkpoint["config"].get("imagination_termination", "learned")
    temperature = checkpoint["config"].get("termination_smoothing_temperature", 0.05)
    clip = torch.arange(40, device="cuda").repeat(3)
    fractions = torch.tensor([0.0, 0.25, 0.5], device="cuda").repeat_interleave(40)
    frame = ((motions.lengths[clip] - 1) * fractions).long()
    reference = motions.get(clip, frame)
    sim = G1Simulator(120)
    sim.reset(reference["qpos"], reference["qvel"])
    previous_action = torch.zeros((120, 29), device="cuda")
    real = torch.cat((sim.qpos, sim.qvel, previous_action), -1)
    open_prediction, closed_prediction = real.clone(), real.clone()
    real_history = observation(sim.qpos, sim.qvel, previous_action, sim.q0, sim.context[:, 1:30])[:, None].repeat(1, 10, 1)
    closed_history = real_history.clone()
    alive = torch.ones(120, dtype=torch.bool, device="cuda")
    open_survival = torch.ones(120, device="cuda")
    closed_survival = open_survival.clone()
    horizon_records = []
    safe_sum = terminal_sum = brier_sum = 0.0
    safe_count = terminal_count = 0
    first_failure_pairs = []
    paired = {m: {"safe_sum": 0.0, "terminal_sum": 0.0, "brier_sum": 0.0,
                  "open_survival": torch.ones(120, device="cuda"),
                  "closed_survival": torch.ones(120, device="cuda"), "horizons": []}
              for m in ("learned", "analytic_smooth")} if compare_termination else {}
    for step in range(1, 33):
        goal = motions.goal(clip, frame + step - 1)
        action = actor(real_history, goal)
        closed_action = actor(closed_history, goal)
        qpos, qvel = sim.step(action)
        real = torch.cat((qpos, qvel, action), -1)
        open_prediction = world(open_prediction, action, sim.context)
        closed_prediction = world(closed_prediction, closed_action, sim.context)
        ref = motions.get(clip, frame + step)["qpos"]
        done = hard_failure(real, ref)
        actual_probability = world.termination_probability(real, ref, mode, temperature)
        open_probability = world.termination_probability(open_prediction, ref, mode, temperature)
        closed_probability = world.termination_probability(closed_prediction, ref, mode, temperature)
        safe, first_terminal = alive & ~done, alive & done
        paired_probabilities = {}
        for paired_mode, stats in paired.items():
            probabilities = [world.termination_probability(s, ref, paired_mode, temperature)
                             for s in (real, open_prediction, closed_prediction)]
            paired_probabilities[paired_mode] = probabilities
            actual_p, open_p, closed_p = probabilities
            stats["safe_sum"] += float(actual_p[safe].sum())
            stats["terminal_sum"] += float(actual_p[first_terminal].sum())
            stats["brier_sum"] += float((actual_p[alive] - done[alive].float()).square().sum())
            stats["open_survival"] *= 1 - open_p
            stats["closed_survival"] *= 1 - closed_p
            if step in (1, 8, 16, 32):
                stats["horizons"].append({"horizon_steps": step,
                    "predicted_open_loop_survival": float(stats["open_survival"].mean()),
                    "predicted_closed_loop_survival": float(stats["closed_survival"].mean())})
        safe_sum += float(actual_probability[safe].sum())
        terminal_sum += float(actual_probability[first_terminal].sum())
        brier_sum += float((actual_probability[alive] - done[alive].float()).square().sum())
        safe_count += int(safe.sum())
        terminal_count += int(first_terminal.sum())
        for sample in torch.nonzero(first_terminal).flatten().tolist():
            first_failure_pairs.append({"motion": motions.names[int(clip[sample])], "start_fraction": float(fractions[sample]),
                "step": step, "real_height_error_m": float((real[sample, 2] - ref[sample, 2]).abs()),
                "open_model_height_error_m": float((open_prediction[sample, 2] - ref[sample, 2]).abs()),
                "closed_model_height_error_m": float((closed_prediction[sample, 2] - ref[sample, 2]).abs()),
                "probability_on_real_state": float(actual_probability[sample]),
                "probability_on_open_model_state": float(open_probability[sample]),
                "probability_on_closed_model_state": float(closed_probability[sample])})
            if compare_termination:
                first_failure_pairs[-1]["counterfactual_probabilities_on_same_states"] = {
                    m: {key: float(p[sample]) for key, p in zip(("real", "open_model", "closed_model"), probabilities)}
                    for m, probabilities in paired_probabilities.items()}
        valid = alive.clone()
        alive &= ~done
        open_survival *= 1 - open_probability
        closed_survival *= 1 - closed_probability
        real_obs = observation(qpos, qvel, action, sim.q0, sim.context[:, 1:30])
        closed_obs = observation(closed_prediction[:, :36], closed_prediction[:, 36:71], closed_action, sim.q0, sim.context[:, 1:30])
        real_history = torch.cat((real_history[:, 1:], real_obs[:, None]), 1)
        closed_history = torch.cat((closed_history[:, 1:], closed_obs[:, None]), 1)
        if step in (1, 8, 16, 32):
            horizon_records.append({"horizon_steps": step, "horizon_seconds": step*0.02,
                "actual_survival_fraction": float(alive.float().mean()),
                "predicted_open_loop_survival": float(open_survival.mean()),
                "predicted_closed_loop_survival": float(closed_survival.mean()),
                "open_loop_all_samples": errors(open_prediction, real, torch.ones_like(alive)),
                "open_loop_before_first_failure": errors(open_prediction, real, valid),
                "closed_loop_before_first_failure": errors(closed_prediction, real, valid),
                "closed_vs_real_action_rmse": float((closed_action - action).square().mean().sqrt())})
    result = {"iteration": checkpoint["iteration"], "actor_updates": checkpoint["actor_updates"],
        "imagination_termination": mode, "termination_smoothing_temperature": temperature,
        "termination_mode_override": termination_mode,
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "dataset_manifest_sha256": motions.manifest_hash, "motions": 40, "starts": 120,
        "start_fractions": [0.0, 0.25, 0.5], "observations_and_actions_noiseless": True,
        "context": "nominal: foot friction 1.0, zero calibration and CoM offsets",
        "open_loop_definition": "world model receives the same executed actions as the physical rollout",
        "closed_loop_definition": "policy receives predicted states through its observation history",
        "termination_head_on_true_states": {"safe_state_count": safe_count, "first_terminal_count": terminal_count,
            "mean_probability_on_safe_states": safe_sum/max(safe_count, 1),
            "mean_probability_on_first_terminal_states": terminal_sum/terminal_count if terminal_count else None,
            "brier_score": brier_sum/max(safe_count+terminal_count, 1)},
        "horizons": horizon_records, "first_failure_pairs": first_failure_pairs,
        "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "wall_seconds": time.monotonic()-started,
        "scope": "Matched short-horizon mechanism diagnostic; complete-motion success is evaluated separately"}
    if compare_termination:
        result["paired_termination_comparison"] = {
            "same_physical_and_predicted_states": True, "same_actions": True,
            "interpretation": "Both probability functions evaluated inside one rollout; no policy or dynamics update",
            "safe_state_count": safe_count, "first_terminal_count": terminal_count,
            "modes": {m: {"mean_probability_on_safe_states": s["safe_sum"] / max(safe_count, 1),
                          "mean_probability_on_first_terminal_states": s["terminal_sum"] / terminal_count if terminal_count else None,
                          "brier_score": s["brier_sum"] / max(safe_count + terminal_count, 1),
                          "horizons": s["horizons"]} for m, s in paired.items()}}
    target = output_path or output_dir / f"diagnostics_{checkpoint['iteration']:07d}.json"
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("MODEL_DIAGNOSTIC_COMPLETE", json.dumps(result, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--termination-mode", choices=("learned", "analytic_smooth"))
    parser.add_argument("--compare-termination", action="store_true",
                        help="Evaluate both probability rules on the exact same rollout states")
    args = parser.parse_args()
    if (args.termination_mode or args.compare_termination) and not args.output:
        raise ValueError("A counterfactual termination mode requires a separate output path")
    with pin_checkpoint(args.checkpoint) as pinned:
        diagnose(pinned, args.checkpoint.absolute().parent, args.output, args.termination_mode, args.compare_termination)


if __name__ == "__main__":
    main()
