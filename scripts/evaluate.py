"""Deterministic complete-motion evaluation, shared by both learned methods."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from supermimic.motion import MotionLibrary
from supermimic.simulator import G1Simulator
from supermimic.kinematics import ForwardKinematics
from supermimic.networks import Actor
from supermimic.task import observation, reward_and_termination
from supermimic.checkpointing import pin_checkpoint


@torch.no_grad()
def evaluate(checkpoint_path, output_dir):
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    checkpoint = torch.load(checkpoint_path, map_location="cuda", weights_only=False)
    checkpoint_hash = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    motions = MotionLibrary(ROOT / "data/processed/lafan1_g1_50hz", "cuda")
    if checkpoint["dataset_manifest_sha256"] != motions.manifest_hash:
        raise ValueError("Evaluation dataset changed after training")
    started = time.monotonic()
    actor = Actor().cuda().eval()
    actor.load_state_dict(checkpoint["actor"])
    sim = G1Simulator(40)
    fk = ForwardKinematics(sim.host_model).float().cuda()
    clip = torch.arange(40, device="cuda")
    frame = torch.zeros(40, device="cuda", dtype=torch.long)
    initial = motions.get(clip, frame)
    sim.reset(initial["qpos"], initial["qvel"])
    previous_action = torch.zeros((40, 29), device="cuda")
    obs = observation(sim.qpos, sim.qvel, previous_action, sim.q0, sim.context[:, 1:30])
    history = obs[:, None].repeat(1, 10, 1)
    active = torch.ones(40, dtype=torch.bool, device="cuda")
    failed = torch.zeros_like(active)
    steps = torch.zeros_like(frame)
    returns = torch.zeros(40, device="cuda")
    root_errors = torch.zeros_like(returns)
    reasons = ["completed"] * 40
    while bool(active.any()):
        action = actor(history, motions.goal(clip, frame))
        qpos, qvel = sim.step(action)
        reference = motions.get(clip, frame + 1)
        reward, done, metrics = reward_and_termination(fk(qpos, qvel), reference, qpos, action, previous_action, sim.soft_lower, sim.soft_upper)
        invalid = ~(torch.isfinite(qpos).all(-1) & torch.isfinite(qvel).all(-1) & torch.isfinite(reward))
        done |= invalid
        returns += torch.where(active & ~invalid, reward, 0)
        root_errors += torch.where(active & ~invalid, metrics["root_position_error_m"], 0)
        steps += active.long()
        just_failed = active & done
        for i in torch.nonzero(just_failed).flatten().tolist():
            reasons[i] = "nonfinite" if invalid[i] else ("root_height" if metrics["root_height_error_m"][i] > 0.25 else "root_tilt")
        failed |= just_failed
        active &= ~(done | (frame + 1 >= motions.lengths - 1))
        frame += 1
        obs = observation(qpos, qvel, action, sim.q0, sim.context[:, 1:30])
        history = torch.cat((history[:, 1:], obs[:, None]), 1)
        previous_action = action
        ids = torch.nonzero(~active).flatten()
        if len(ids):
            sim.reset(initial["qpos"][ids], initial["qvel"][ids], ids)
    records = []
    for i, name in enumerate(motions.names):
        length = int(motions.lengths[i]) - 1
        records.append({"motion": name, "failed": bool(failed[i]), "reason": reasons[i],
                        "executed_steps": int(steps[i]), "full_reference_steps": length,
                        "completion_fraction": int(steps[i])/length, "normalized_return": float(returns[i])/(0.1*length),
                        "root_position_error_before_failure_m": float(root_errors[i])/max(int(steps[i]), 1)})
    result = {"status": "evaluated", "method": checkpoint["config"]["method"],
              "iteration": checkpoint["iteration"], "actor_updates": checkpoint["actor_updates"],
              "dataset_manifest_sha256": motions.manifest_hash,
              "checkpoint_sha256": checkpoint_hash,
              "motions": 40, "failed_motions": sum(r["failed"] for r in records),
              "mean_normalized_return": sum(r["normalized_return"] for r in records)/40,
              "mean_completion_fraction": sum(r["completion_fraction"] for r in records)/40,
              "wall_seconds": time.monotonic()-started, "clips": records,
              "protocol": {"start_frame": 0, "short_prefix_cap": None, "deterministic_actor": True,
                           "friction": 1.0, "observation_noise": False, "domain_randomization": False,
                           "failure": "root height error > 0.25 m OR gravity-z difference > 0.8 OR nonfinite",
                           "normalization": "0.1 * full reference transitions; unexecuted failed tail contributes zero",
                           "scope": "training-motion coverage; not unseen-motion generalization"}}
    text = json.dumps(result, indent=2) + "\n"
    with (output_dir / ".evaluation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = output_dir / f"evaluation_{checkpoint['iteration']:07d}.json"
        temp = target.with_suffix(f".{os.getpid()}.tmp")
        temp.write_text(text)
        temp.replace(target)
        latest = output_dir / "evaluation.json"
        previous_iteration = json.loads(latest.read_text())["iteration"] if latest.exists() else -1
        if checkpoint["iteration"] >= previous_iteration:
            temp = latest.with_suffix(f".{os.getpid()}.tmp")
            temp.write_text(text)
            temp.replace(latest)
    print("FULL_EVALUATION_COMPLETE", json.dumps({k:v for k,v in result.items() if k not in ("clips", "protocol")}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()
    output_dir = args.checkpoint.absolute().parent
    # Pin the exact version once. A moving latest symlink must never make the
    # evaluated policy and its recorded checksum refer to different iterations.
    with pin_checkpoint(args.checkpoint) as stable:
        evaluate(stable, output_dir)


if __name__ == "__main__":
    main()
