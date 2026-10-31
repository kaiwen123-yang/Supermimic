"""Run real G1 learning. Both methods use the same physical task and actor."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from supermimic.motion import MotionLibrary
from supermimic.environment import TrackingEnvironment
from supermimic.learning import SuperMimic, PPOSim


def save(learner, cfg, directory, iteration, elapsed, dataset_hash, actor_updates):
    checkpoint = learner.checkpoint()
    checkpoint.update(config=cfg, iteration=iteration, actor_updates=actor_updates,
                      dataset_manifest_sha256=dataset_hash, elapsed_seconds=elapsed,
                      sampler_returns=learner.env.sampler.returns, sampler_memory=learner.env.sampler.memory,
                      torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all())
    temp = directory / "checkpoint.tmp"
    torch.save(checkpoint, temp)
    target = directory / f"checkpoint_{iteration:07d}.pt"
    temp.replace(target)
    # Retain real intermediate checkpoints for full-clip learning curves. The
    # latest alias is a symlink, not a second large copy of the checkpoint.
    alias = directory / "checkpoint-link.tmp"
    if alias.exists() or alias.is_symlink():
        alias.unlink()
    alias.symlink_to(target.name)
    alias.replace(directory / "checkpoint_latest.pt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("supermimic", "ppo_sim"), required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/lafan40.json")
    parser.add_argument("--run", required=True)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    cfg["method"] = args.method
    cfg["num_envs"] = cfg["supermimic_num_envs"] if args.method == "supermimic" else cfg["ppo_num_envs"]
    directory = ROOT / "outputs/runs" / args.run
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    metadata = {"gpu": torch.cuda.get_device_name(), "gpu_shared": True, "torch": torch.__version__,
                "started_unix": time.time(), "pid": os.getpid(), "seed": cfg["seed"],
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                "other_gpu_processes": subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv"], text=True),
                "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for directory_name in ("supermimic", "scripts", "configs")
                                  for p in (ROOT / directory_name).rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".json", ".toml")}}
    (directory / "runtime.json").write_text(json.dumps(metadata, indent=2) + "\n")
    learner = None
    iteration = 0
    actor_updates = 0
    try:
        motions = MotionLibrary(ROOT / "data/processed/lafan1_g1_50hz", "cuda:0")
        env = TrackingEnvironment(motions, cfg["num_envs"], cfg["max_episode_steps"])
        if cfg["compile_fk"]:
            env.fk.forward = torch.compile(env.fk.forward, dynamic=True)
        # The two methods start from matching network initialization even though
        # their paper environment counts differ.
        torch.manual_seed(cfg["seed"] + 1000)
        learner = SuperMimic(env, cfg) if args.method == "supermimic" else PPOSim(env, cfg)
        first_iteration = 0
        if args.resume:
            previous = torch.load(args.resume, map_location="cuda", weights_only=False)
            if previous["config"]["method"] != args.method or previous["dataset_manifest_sha256"] != motions.manifest_hash:
                raise ValueError("Resume method/dataset mismatch")
            learner.actor.load_state_dict(previous["actor"])
            learner.critic.load_state_dict(previous["critic"])
            if args.method == "supermimic":
                learner.world.load_state_dict(previous["world_model"])
                for name in ("actor", "critic", "world"):
                    getattr(learner, name + "_opt").load_state_dict(previous[name + "_optimizer"])
            else:
                learner.log_std.data.copy_(previous["log_std"])
                learner.optimizer.load_state_dict(previous["optimizer"])
            learner.env.sampler.returns.copy_(previous["sampler_returns"])
            learner.env.sampler.memory.copy_(previous["sampler_memory"])
            learner.collected_steps = previous["collected_steps"]
            first_iteration = previous["iteration"]
            actor_updates = previous["actor_updates"]
            torch.set_rng_state(previous["torch_rng"].cpu())
            torch.cuda.set_rng_state_all([value.cpu() for value in previous["cuda_rng"]])
        save(learner, cfg, directory, first_iteration, time.monotonic() - started, motions.manifest_hash, actor_updates)
        if args.method == "supermimic":
            print("REPLAY_WARMUP", cfg["replay_warmup_steps"], flush=True)
            learner.collect(cfg["replay_warmup_steps"])
        print("LEARNING_STARTED", args.method, cfg["num_envs"], flush=True)
        with (directory / "metrics.jsonl").open("a", buffering=1) as log:
            for iteration in range(first_iteration + 1, cfg["max_iterations"] + 1):
                if time.monotonic() - started >= cfg["max_hours"] * 3600:
                    iteration -= 1
                    break
                start = time.monotonic()
                if args.method == "supermimic":
                    learner.set_schedule(iteration)
                    metrics = learner.collect(2 if iteration % 2 else 3)
                    torch.cuda.synchronize()
                    after_collect = time.monotonic()
                    metrics.update(learner.fit_world())
                    torch.cuda.synchronize()
                    after_world = time.monotonic()
                    if iteration > cfg["world_only_warmup_iterations"]:
                        metrics.update(learner.improve_policy())
                        actor_updates += 1
                    torch.cuda.synchronize()
                    metrics.update(collection_seconds=after_collect-start, world_seconds=after_world-after_collect,
                                   policy_critic_seconds=time.monotonic()-after_world)
                else:
                    data = learner.collect()
                    torch.cuda.synchronize()
                    after_collect = time.monotonic()
                    metrics = learner.update(data)
                    actor_updates += 1
                    torch.cuda.synchronize()
                    metrics.update(collection_seconds=after_collect-start, policy_critic_seconds=time.monotonic()-after_collect)
                metrics.update(iteration=iteration, actor_updates=actor_updates, elapsed_seconds=time.monotonic()-started,
                               collected_sim_transitions=learner.collected_steps,
                               torch_peak_allocated_mib=torch.cuda.max_memory_allocated()/1024**2)
                log.write(json.dumps(metrics, allow_nan=False) + "\n")
                if iteration % cfg["log_every_iterations"] == 0:
                    print(json.dumps(metrics, allow_nan=False), flush=True)
                if iteration % cfg["checkpoint_every_iterations"] == 0:
                    save(learner, cfg, directory, iteration, time.monotonic()-started, motions.manifest_hash, actor_updates)
        save(learner, cfg, directory, iteration, time.monotonic()-started, motions.manifest_hash, actor_updates)
        status = {"status": "budget_completed", "method": args.method, "iteration": iteration, "actor_updates": actor_updates,
                  "sim_transitions": learner.collected_steps, "wall_seconds": time.monotonic()-started,
                  "full_clip_evaluation_done": False, "qualification_pass": False}
        (directory / "status.json").write_text(json.dumps(status, indent=2) + "\n")
        print("TRAINING_BUDGET_COMPLETE", json.dumps(status), flush=True)
    except Exception as exc:
        failure = {"status": "failed", "iteration": iteration, "actor_updates": actor_updates,
                   "exception": repr(exc), "traceback": traceback.format_exc(), "wall_seconds": time.monotonic()-started}
        (directory / "failure.json").write_text(json.dumps(failure, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
