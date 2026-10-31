"""One-time transition of the existing campaign at its next saved milestone.

Scoped to one explicit run/PID/tmux session; no polling service or general
scheduler is installed. The old worker is stopped only after its complete
checkpoint has been read successfully. Other jobs are never signaled.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--iteration", type=int, default=1000)
    args = parser.parse_args()
    run_name = args.tag + "-supermimic"
    run = ROOT / "outputs/runs" / run_name
    checkpoint = run / f"checkpoint_{args.iteration:07d}.pt"
    cmdline_path = Path(f"/proc/{args.pid}/cmdline")
    expected = ["scripts/train.py", "--method", "supermimic", "--config", "configs/lafan40.json", "--run", run_name]
    def validate_worker():
        command = cmdline_path.read_bytes().decode().split("\x00")
        if not all(x in command for x in expected) or Path(f"/proc/{args.pid}/cwd").resolve() != ROOT:
            raise RuntimeError("Worker identity changed; refusing to signal it")
    validate_worker()
    report = {"status": "waiting_for_checkpoint", "run": run_name, "pid": args.pid,
              "iteration": args.iteration, "started_unix": time.time()}
    report_path = ROOT / "outputs/campaigns" / f"{args.tag}.checkpoint-policy-switch.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    import torch
    deadline = time.monotonic() + 5400
    while not checkpoint.exists():
        validate_worker()
        if time.monotonic() >= deadline:
            raise TimeoutError("The next checkpoint did not arrive within the bounded transition window")
        time.sleep(1)
    state = torch.load(checkpoint, map_location="cpu", weights_only=False, mmap=True)
    if state["iteration"] != args.iteration or state["config"]["method"] != "supermimic":
        raise RuntimeError("Unexpected checkpoint payload")
    required = ("actor", "critic", "world_model", "actor_optimizer", "critic_optimizer", "world_optimizer",
                "torch_rng", "cuda_rng", "sampler_returns", "sampler_memory")
    if not all(key in state for key in required):
        raise RuntimeError("Checkpoint lacks required continuation state")
    h = hashlib.sha256()
    with checkpoint.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024**2), b""):
            h.update(chunk)
    report.update(checkpoint_sha256=h.hexdigest(), saved_actor_updates=state["actor_updates"],
                  saved_elapsed_seconds=state["elapsed_seconds"], status="checkpoint_verified")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    del state
    validate_worker()
    os.kill(args.pid, signal.SIGTERM)
    for _ in range(60):
        if not cmdline_path.exists():
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Old worker did not exit; no second worker started")
    for _ in range(60):
        dead = subprocess.check_output(["tmux", "list-panes", "-t", args.session, "-F", "#{pane_dead}"], text=True).strip()
        if dead == "1":
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Old campaign wrapper has not exited")
    command = "bash " + shlex.join([str(ROOT / "scripts/resume_lafan40_d57.sh"), args.tag, str(checkpoint)])
    subprocess.run(["tmux", "respawn-pane", "-t", args.session, command], check=True)
    report.update(status="resumed", resumed_unix=time.time(), replay_rebuild_expected=True,
                  note="Saved parameter/optimizer updates retained; simulator and replay are rebuilt, so continuation is not bitwise identical.")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print("CHECKPOINT_POLICY_SWITCHED", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
