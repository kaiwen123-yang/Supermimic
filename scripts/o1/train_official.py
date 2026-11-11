"""O1's bounded local-artifact runner; learning calls are the upstream loop."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time

PROCESS_STARTED = time.monotonic()

import torch
import wandb
import supermimic.tasks  # noqa: F401
from mjlab.tasks.registry import load_env_cfg
from supermimic.runners.supermimic_runner import Ratio, SuperMimicRunner, SuperMimicRunnerCfg
from supermimic.scripts.train_utils import create_env, setup_device

from common import CAMPAIGN, RUN_NAME, TASK, now, write_json


class O1Runner(SuperMimicRunner):
    def run_segment(self, workspace: Path, started: float, previous_seconds: float) -> None:
        run_dir = workspace / "outputs" / RUN_NAME
        result_dir = workspace / "results" / CAMPAIGN
        run_dir.mkdir(parents=True, exist_ok=True)
        self.counts = {"collection_steps": 0, "real_transitions": 0, "learning_phases": 0,
                       "world_model_batch_updates": 0, "actor_updates": 0, "critic_minibatch_updates": 0}
        versions = {name: subprocess.check_output(["git", "-C", str(workspace / name), "rev-parse", "HEAD"], text=True).strip()
                    for name in ["supermimic", "mjlab_research"]}
        actual = {"task_id": TASK, "seed": 0, "env_cfg": asdict(self.env.cfg),
                  "runner_cfg": asdict(self.cfg), "source_commits": versions,
                  "baseline": "official_current_main_GenCoord_proprio_history10",
                  "full_resume": False, "budget_seconds": 43200,
                  "previous_training_seconds": previous_seconds}
        write_json(run_dir / "actual_config.json", actual)
        write_json(result_dir / "actual_config.json", actual)
        wandb.init(project="supermimic", name=RUN_NAME, mode="offline", dir=str(run_dir), config=actual)
        self.env.reset()
        self._seed_sim_history()
        should_train = Ratio(self.env.num_envs / self.cfg.wm.num_batches / self.cfg.wm.batch_size / self.cfg.wm.horizon * self.cfg.replay_ratio)
        next_node = 0
        nodes = [10800, 21600, 43200]
        log_started = time.monotonic()
        wm_time = policy_time = 0.0
        collected_since_log = 0
        loss_dict = {}
        log_count = 0

        def elapsed():
            return previous_seconds + time.monotonic() - started

        def progress(status, **extra):
            record = {"campaign": CAMPAIGN, "run_name": RUN_NAME, "status": status,
                      "updated_at": now(), "training_seconds": elapsed(),
                      "source_commits": versions, **self.counts, **extra}
            write_json(run_dir / "progress.json", record)
            return record

        def save(label=None):
            step = self.counts["collection_steps"]
            target = run_dir / "checkpoints" / f"checkpoint_{step:09d}.pt"
            target.parent.mkdir(parents=True, exist_ok=True)
            metadata = progress("running", checkpoint=str(target), evaluation_label=label)
            torch.save({"world_model": self._wm.bundle(), "actor": self.policy_learner.actor.state_dict(),
                        "critic": self.policy_learner.critic.state_dict(), "runner_cfg": asdict(self.cfg),
                        "metadata": metadata}, target)
            write_json(target.with_suffix(".json"), metadata)
            if label is not None:
                log = run_dir / f"evaluation_{label}.log"
                with log.open("w") as stream:
                    subprocess.Popen([sys.executable, str(Path(__file__).with_name("evaluate_publish.py")),
                                      "--workspace", str(workspace), "--checkpoint", str(target), "--label", label],
                                     stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                print(f"O1_FIXED_NODE label={label} checkpoint={target} training_seconds={metadata['training_seconds']:.3f}", flush=True)
            return target

        progress("running")
        reason = "upstream_iteration_limit"
        final_checkpoint = None
        for step in range(self.cfg.max_iterations):
            collected = self.step()
            collected_since_log += collected
            self.counts["collection_steps"] += 1
            self.counts["real_transitions"] += collected
            for _ in range(should_train(step)):
                if self.replay_buffer.num_transitions < self.cfg.wm.horizon:
                    continue
                data = (self.replay_buffer.sample(self.cfg.wm.horizon, self.cfg.wm.batch_size)
                        for _ in range(self.cfg.wm.num_batches))
                tick = time.monotonic()
                wm_logs = self.world_model_learner.update(data)
                wm_time += time.monotonic() - tick
                tick = time.monotonic()
                policy_logs = self.policy_learner.update()
                policy_time += time.monotonic() - tick
                loss_dict.update(wm_logs)
                loss_dict.update(policy_logs)
                self.counts["learning_phases"] += 1
                self.counts["world_model_batch_updates"] += self.cfg.wm.num_batches
                self.counts["actor_updates"] += self.cfg.policy.num_batches
                self.counts["critic_minibatch_updates"] += 20 * self.cfg.policy.num_batches
            if step % self.cfg.log_interval == 0:
                self.logger.log(it=log_count, total_it=self.cfg.max_iterations // self.cfg.log_interval,
                                collect_time=time.monotonic() - log_started - wm_time - policy_time,
                                wm_learn_time=wm_time, policy_learn_time=policy_time,
                                loss_dict=loss_dict, num_collected_steps=collected_since_log)
                log_count += 1
                log_started = time.monotonic()
                wm_time = policy_time = 0.0
                collected_since_log = 0
                progress("running")
                if (run_dir / "stop_after_success.json").exists():
                    reason = "formal_return_target_reached"
                    break
            if elapsed() >= 43200:
                reason = "training_time_budget"
                break
            if next_node < 2 and elapsed() >= nodes[next_node]:
                save(f"hour_{nodes[next_node] // 3600:02d}")
                next_node += 1
            elif step % self.cfg.save_interval == 0:
                save()
        final_checkpoint = save("final")
        completed = progress("training_completed_evaluation_pending", stop_reason=reason,
                             checkpoint=str(final_checkpoint), training_finished_at=now())
        write_json(result_dir / "training_endpoint.json", completed)
        self._cleanup()
        print(f"O1_TRAINING_COMPLETED reason={reason} checkpoint={final_checkpoint}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--previous-training-seconds", type=float, default=0.0)
    args = parser.parse_args()
    run_dir = args.workspace / "outputs" / RUN_NAME
    started = PROCESS_STARTED
    write_json(run_dir / "progress.json", {"status": "initializing", "started_at": now(),
                                         "previous_training_seconds": args.previous_training_seconds})
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(0)
    device = setup_device("cuda:0")
    cfg = load_env_cfg(TASK, play=False)
    cfg.seed = 0
    manifest = json.loads((args.workspace / "data/lafan40_official_npz/manifest.json").read_text())
    cfg.commands["motion"].motion_file = [clip["official_motion_path"] for clip in manifest["clips"]]
    cfg.commands["motion"].sampling_mode = "external"
    runner_cfg = SuperMimicRunnerCfg(run_name=RUN_NAME, representation="gencoord", actor_obs="proprio", history_length=10)
    try:
        env = create_env(cfg, 4096, device)
        runner = O1Runner(env, runner_cfg, TASK, registry_name=None, device=device)
        runner.run_segment(args.workspace, started, args.previous_training_seconds)
    except BaseException as error:
        write_json(run_dir / "failure.json", {"status": "failed", "recorded_at": now(),
                   "training_seconds": args.previous_training_seconds + time.monotonic() - started,
                   "error_type": type(error).__name__, "error": str(error)})
        raise


if __name__ == "__main__":
    main()
