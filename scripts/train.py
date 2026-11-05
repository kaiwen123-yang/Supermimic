"""Run real G1 learning. Both methods use the same physical task and actor."""
from pathlib import Path
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from supermimic.motion import MotionLibrary, checkpoint_data_definition
from supermimic.environment import TrackingEnvironment
from supermimic.learning import SuperMimic, PPOSim
from supermimic.checkpointing import save_checkpoint


def save(learner, cfg, directory, iteration, elapsed, dataset_definition, actor_updates):
    checkpoint = learner.checkpoint()
    checkpoint.update(config=cfg, iteration=iteration, actor_updates=actor_updates,
                      data_definition=dataset_definition, elapsed_seconds=elapsed,
                      sampler_returns=learner.env.sampler.returns, sampler_memory=learner.env.sampler.memory,
                      torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all())
    return save_checkpoint(checkpoint, directory, cfg.get("keep_recent_checkpoints", 20),
                           cfg.get("publish_every_iterations", 1000))


def request_publication(directory, iteration, cfg):
    every = cfg.get("publish_every_iterations", 0)
    if every <= 0 or iteration <= 0 or iteration % every:
        return
    session = f"sm-pub-{directory.name}-{iteration:07d}"
    if subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0:
        return
    command = shlex.join([str(ROOT / "scripts/publish_checkpoint_d57.sh"), directory.name, str(iteration)])
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "bash " + command], check=True)
    subprocess.run(["tmux", "set-option", "-t", session, "remain-on-exit", "on"], check=True)
    print("PUBLICATION_QUEUED", iteration, session, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("supermimic", "ppo_sim"), required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/lafan40.json")
    parser.add_argument("--run", required=True)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--resume-in-place", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    cfg["method"] = args.method
    cfg.setdefault("world_termination_loss", "aux_bce")
    cfg["num_envs"] = cfg["supermimic_num_envs"] if args.method == "supermimic" else cfg["ppo_num_envs"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.run):
        raise ValueError("Unsafe run name")
    directory = ROOT / "outputs/runs" / args.run
    if args.resume_in_place:
        if not args.resume or args.resume.resolve().parent != directory.resolve():
            raise ValueError("In-place resume requires a checkpoint from this run")
        resume_number = int(re.fullmatch(r"checkpoint_(\d+)\.pt", args.resume.resolve().name).group(1))
        existing_numbers = [int(m.group(1)) for p in directory.glob("checkpoint_*.pt")
                            if (m := re.fullmatch(r"checkpoint_(\d+)\.pt", p.name))]
        if max(existing_numbers) != resume_number:
            raise ValueError("In-place continuation requires the newest checkpoint; use a new run name for rollback")
    else:
        directory.mkdir(parents=True, exist_ok=False)
    attempt = str(int(time.time()))
    if args.resume_in_place:
        history_dir = directory / "resume_history" / attempt
        history_dir.mkdir(parents=True)
        for name in ("config.json", "runtime.json", "status.json", "failure.json"):
            if (directory / name).exists():
                (directory / name).replace(history_dir / name)
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
                "other_gpu_processes": subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv"], text=True)}
    (directory / "runtime.json").write_text(json.dumps(metadata, indent=2) + "\n")
    learner = None
    iteration = 0
    actor_updates = 0
    elapsed_offset = 0.0
    stage_started = started
    stage_elapsed = lambda: time.monotonic() - stage_started
    elapsed = lambda: elapsed_offset + time.monotonic() - started
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
            if previous["config"]["method"] != args.method or checkpoint_data_definition(previous) != motions.data_definition:
                raise ValueError("Resume method/dataset mismatch")
            if previous["config"].get("goal_frame", "reference_heading") != cfg.get("goal_frame", "reference_heading"):
                raise ValueError("Resume cannot change goal semantics")
            if (cfg.get("actor_root_position_feedback", False) and
                    previous["actor"]["encoder.0.weight"].shape[1] == 710):
                # Only the known P5 710 -> P6 713 migration; retain Adam step.
                weight = previous["actor"]["encoder.0.weight"]
                previous["actor"]["encoder.0.weight"] = torch.cat((weight, weight.new_zeros((2048, 3))), dim=1)
                actor_optimizer = previous["actor_optimizer"]
                parameter_id = actor_optimizer["param_groups"][0]["params"][0]
                for key in ("exp_avg", "exp_avg_sq"):
                    moment = actor_optimizer["state"][parameter_id][key]
                    actor_optimizer["state"][parameter_id][key] = torch.cat((moment, moment.new_zeros((2048, 3))), dim=1)
                metadata["actor_input_migration"] = "710->713: three zero weight/Adam moment columns; all other state retained"
                print("ACTOR_POSITION_MIGRATION", metadata["actor_input_migration"], flush=True)
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
            iteration = first_iteration
            actor_updates = previous["actor_updates"]
            elapsed_offset = float(previous["elapsed_seconds"])
            torch.set_rng_state(previous["torch_rng"].cpu())
            torch.cuda.set_rng_state_all([value.cpu() for value in previous["cuda_rng"]])
            if args.resume_in_place and (directory / "metrics.jsonl").exists():
                old_lines = (directory / "metrics.jsonl").read_text().splitlines(keepends=True)
                keep, superseded = [], []
                for line in old_lines:
                    if not line.endswith("\n") or json.loads(line)["iteration"] > first_iteration:
                        superseded.append(line)
                    else:
                        keep.append(line)
                if superseded:
                    (history_dir / "superseded_after_checkpoint.jsonl").write_text("".join(superseded))
                    temp = directory / "metrics-resume.tmp"
                    temp.write_text("".join(keep))
                    temp.replace(directory / "metrics.jsonl")
            metadata.update(resumed_from=str(args.resume), resume_iteration=first_iteration,
                            previous_elapsed_seconds=elapsed_offset, replay_rebuilt=True,
                            optimizer_state_restored=True, sampler_state_restored=True, previous_simulator_state_restored=False,
                            parent_world_termination_loss=previous["config"].get("world_termination_loss", "aux_bce"),
                            world_termination_loss=cfg["world_termination_loss"],
                            rng_restored="parent torch CPU and all CUDA states; NumPy initialized with unchanged seed")
            (directory / "runtime.json").write_text(json.dumps(metadata, indent=2) + "\n")
            del previous
        stage_started = time.monotonic()
        if args.resume:
            started = stage_started
        initial_actor_updates = actor_updates
        initial_transitions = learner.collected_steps
        metadata.update(stage_started_unix=time.time(), budget_clock="new stage including replay warmup",
                        start_iteration=first_iteration, target_iteration=cfg["max_iterations"],
                        previous_elapsed_seconds=elapsed_offset,
                        initialization="resume" if args.resume else "scratch")
        if not args.resume:
            metadata.update(optimizer_state_restored=False, sampler_state_restored=False,
                            rng_restored=False, replay_initial_fill_steps=cfg["replay_warmup_steps"])
        (directory / "runtime.json").write_text(json.dumps(metadata, indent=2) + "\n")
        if not args.resume_in_place:
            save(learner, cfg, directory, first_iteration, elapsed(), motions.data_definition, actor_updates)
        if args.method == "supermimic":
            print("REPLAY_WARMUP", cfg["replay_warmup_steps"], flush=True)
            warmup = learner.collect(cfg["replay_warmup_steps"])
            (directory / "warmup.json").write_text(json.dumps(warmup, indent=2) + "\n")
        print("LEARNING_STARTED", args.method, cfg["num_envs"], flush=True)
        with (directory / "metrics.jsonl").open("a", buffering=1) as log:
            for iteration in range(first_iteration + 1, cfg["max_iterations"] + 1):
                if stage_elapsed() >= cfg["max_hours"] * 3600:
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
                        metrics.update(learner.improve_policy(iteration, directory / "training_evidence"))
                        actor_updates += 1
                    torch.cuda.synchronize()
                    metrics.update(collection_seconds=after_collect-start, world_seconds=after_world-after_collect,
                                   policy_critic_seconds=time.monotonic()-after_world)
                    metrics.update({name + "_learning_rate": getattr(learner, name + "_opt").param_groups[0]["lr"]
                                    for name in ("actor", "world", "critic")})
                else:
                    data = learner.collect()
                    torch.cuda.synchronize()
                    after_collect = time.monotonic()
                    metrics = learner.update(data)
                    actor_updates += 1
                    torch.cuda.synchronize()
                    metrics.update(collection_seconds=after_collect-start, policy_critic_seconds=time.monotonic()-after_collect)
                if iteration % cfg["checkpoint_every_iterations"] == 0:
                    metrics["checkpoint_write_seconds"] = save(learner, cfg, directory, iteration, elapsed(), motions.data_definition, actor_updates)
                metrics.update(iteration=iteration, actor_updates=actor_updates, elapsed_seconds=elapsed(),
                               stage_elapsed_seconds=stage_elapsed(), new_training_iterations=iteration-first_iteration,
                               new_joint_updates=actor_updates-initial_actor_updates,
                               new_wm_only_updates=(iteration-first_iteration)-(actor_updates-initial_actor_updates),
                               new_actor_updates=actor_updates-initial_actor_updates,
                               new_sim_transitions=learner.collected_steps-initial_transitions,
                               learning_rate=learner.actor_opt.param_groups[0]["lr"] if args.method=="supermimic" else learner.optimizer.param_groups[0]["lr"],
                               collected_sim_transitions=learner.collected_steps,
                               torch_peak_allocated_mib=torch.cuda.max_memory_allocated()/1024**2)
                log.write(json.dumps(metrics, allow_nan=False) + "\n")
                request_publication(directory, iteration, cfg)
                if iteration % cfg["log_every_iterations"] == 0:
                    print(json.dumps(metrics, allow_nan=False), flush=True)
        if not (directory / f"checkpoint_{iteration:07d}.pt").exists():
            save(learner, cfg, directory, iteration, elapsed(), motions.data_definition, actor_updates)
        status = {"status": "budget_completed", "method": args.method, "iteration": iteration, "actor_updates": actor_updates,
                  "sim_transitions": learner.collected_steps, "wall_seconds": elapsed(),
                  "stage_wall_seconds": stage_elapsed(), "new_training_iterations": iteration-first_iteration,
                  "new_joint_updates": actor_updates-initial_actor_updates,
                  "new_wm_only_updates":(iteration-first_iteration)-(actor_updates-initial_actor_updates),
                  "new_actor_updates": actor_updates-initial_actor_updates,
                  "new_sim_transitions": learner.collected_steps-initial_transitions,
                  "start_iteration": first_iteration, "target_iteration": cfg["max_iterations"],
                  "world_termination_loss": cfg["world_termination_loss"],
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
