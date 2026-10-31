"""Complete-clip diagnostic of an unlearned reference-setpoint PD controller.

One physical rollout per motion, from first frame until natural end or the
paper's failure criterion. Full-duration denominator includes the failed tail.
This is neither SuperMimic training nor the PPO-Sim baseline.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from supermimic.kinematics import ForwardKinematics
from supermimic.motion import MotionLibrary
from supermimic.simulator import G1Simulator
from supermimic.task import reward_and_termination


def gpu_process_memory_mib():
    raw = subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid,used_gpu_memory", "--format=csv,noheader,nounits"], text=True)
    return {int(line.split(",")[0]): int(line.split(",")[1].strip()) for line in raw.splitlines() if line.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-wall-seconds", type=float, default=1800)
    args = parser.parse_args()
    torch.set_num_threads(1)
    started = time.monotonic()
    other_before = gpu_process_memory_mib()
    print("GPU_BEFORE", other_before, flush=True)
    motions = MotionLibrary(ROOT / "data/processed/lafan1_g1_50hz", "cuda:0")
    sim = G1Simulator(args.batch_size)
    fk = ForwardKinematics(sim.host_model).float().cuda()
    records = []
    peak_process_mib = 0
    for start in range(0, len(motions.names), args.batch_size):
        count = min(args.batch_size, len(motions.names) - start)
        clip = torch.arange(start, start + args.batch_size, device="cuda") % len(motions.names)
        frame = torch.zeros(args.batch_size, dtype=torch.long, device="cuda")
        initial = motions.get(clip, frame)
        sim.reset(initial["qpos"], initial["qvel"])
        previous_action = (initial["qpos"][:, 7:] - sim.q0) / sim.action_scale
        active = torch.arange(args.batch_size, device="cuda") < count
        returns = torch.zeros(args.batch_size, device="cuda")
        roots = torch.zeros_like(returns)
        steps = torch.zeros_like(frame)
        failed = torch.zeros_like(active)
        reasons = ["completed"] * args.batch_size
        while bool(active.any()):
            if time.monotonic() - started > args.max_wall_seconds:
                raise RuntimeError("Diagnostic wall budget exhausted; no partial result marked complete")
            next_frame = frame + 1
            ref = motions.get(clip, next_frame)
            action = (ref["qpos"][:, 7:] - sim.q0) / sim.action_scale
            qpos, qvel = sim.step(action)
            with torch.no_grad():
                bodies = fk(qpos, qvel)
                reward, done, metrics = reward_and_termination(bodies, ref, qpos, action, previous_action, sim.soft_lower, sim.soft_upper)
            numerical = ~(torch.isfinite(qpos).all(-1) & torch.isfinite(qvel).all(-1) & torch.isfinite(reward))
            done |= numerical
            returns += torch.where(active & ~numerical, reward, 0)
            roots += torch.where(active & ~numerical, metrics["root_position_error_m"], 0)
            steps += active.long()
            just_failed = active & done
            for i in torch.nonzero(just_failed).flatten().tolist():
                reasons[i] = "nonfinite" if bool(numerical[i]) else ("root_height" if metrics["root_height_error_m"][i] > 0.25 else "root_tilt")
            failed |= just_failed
            complete = next_frame >= motions.lengths[clip] - 1
            active &= ~(done | complete)
            frame = next_frame
            previous_action = action
            # Finished lanes stay at their valid initial state while other lanes run.
            ids = torch.nonzero(~active).flatten()
            if len(ids):
                sim.reset(initial["qpos"][ids], initial["qvel"][ids], ids)
            if int(frame[0]) % 50 == 0:
                memory = gpu_process_memory_mib().get(os.getpid(), 0)
                peak_process_mib = max(peak_process_mib, memory)
        for lane in range(count):
            index = start + lane
            full_steps = int(motions.lengths[index]) - 1
            row = {"motion": motions.names[index], "failed": bool(failed[lane]), "reason": reasons[lane],
                   "executed_steps": int(steps[lane]), "full_reference_steps": full_steps,
                   "completion_fraction": int(steps[lane]) / full_steps,
                   "normalized_return": float(returns[lane]) / (0.1 * full_steps),
                   "mean_root_position_error_before_failure_m": float(roots[lane]) / max(int(steps[lane]), 1)}
            records.append(row)
            print(json.dumps(row), flush=True)
    torch.cuda.synchronize()
    peak_process_mib = max(peak_process_mib, gpu_process_memory_mib().get(os.getpid(), 0))
    result = {"status": "executed", "method": "unlearned_reference_setpoint_PD",
              "is_supermimic_or_ppo": False, "trained_updates": 0, "dataset_manifest_sha256": motions.manifest_hash,
              "clip_count": len(records), "failed_clips": sum(r["failed"] for r in records),
              "mean_normalized_return": sum(r["normalized_return"] for r in records) / len(records),
              "mean_completion_fraction": sum(r["completion_fraction"] for r in records) / len(records),
              "wall_seconds_including_compilation": time.monotonic() - started,
              "torch_peak_allocated_mib": torch.cuda.max_memory_allocated() / 1024**2,
              "sampled_process_peak_mib": peak_process_mib, "other_gpu_processes_before": other_before,
              "gpu_sharing": True, "batch_size": args.batch_size, "clips": records,
              "evaluation": {"friction": 1.0, "observation_noise": False, "domain_randomization": False,
                             "start_frame": 0, "short_prefix_cap": None, "denominator": "0.1 * full reference transitions",
                             "initial_previous_action": "reference first-frame normalized setpoint; no artificial action jump"}}
    out = ROOT / "results/lafan1_g1_preparation/reference_pd.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("REFERENCE_PD_COMPLETE", result["failed_clips"], result["mean_normalized_return"], flush=True)


if __name__ == "__main__":
    main()
