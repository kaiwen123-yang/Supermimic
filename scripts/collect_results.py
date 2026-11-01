"""Copy compact actual run evidence to Git-facing results; keep weights on D57."""
from pathlib import Path
import argparse
import fcntl
import json
import re
import shutil
import statistics
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


def evaluation_summary(evaluation):
    clips = evaluation["clips"]
    seconds = [c["executed_steps"] * 0.02 for c in clips]
    return {"iteration": evaluation["iteration"], "checkpoint_sha256": evaluation["checkpoint_sha256"],
            "motions": len(clips), "completed_motions": len(clips) - evaluation["failed_motions"],
            "mean_executed_seconds": statistics.mean(seconds), "median_executed_seconds": statistics.median(seconds),
            "mean_completion_fraction": evaluation["mean_completion_fraction"],
            "mean_normalized_return": evaluation["mean_normalized_return"],
            "termination_reasons": dict(Counter(c["reason"] for c in clips)),
            "mean_per_motion_root_position_error_m": statistics.mean(c["root_position_error_before_failure_m"] for c in clips)}


def publish_campaign(tag, target_root, campaign):
    from publish_checkpoint import git, URL
    (ROOT / ".cache").mkdir(exist_ok=True)
    with (ROOT / ".cache/publication.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        git("fetch", URL, "main")
        remote_head = git("rev-parse", "FETCH_HEAD")
        worktree = ROOT / ".cache/publication-worktrees" / f"campaign-{tag}-{time.time_ns()}"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        git("worktree", "add", "--detach", str(worktree), remote_head)
        relative = target_root.relative_to(ROOT)
        shutil.copytree(target_root, worktree / relative, dirs_exist_ok=True)
        index_path = worktree / "results/index.json"
        index = json.loads(index_path.read_text())
        index.setdefault("campaigns", {})[tag] = campaign
        index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
        git("add", "--", str(relative), "results/index.json", cwd=worktree)
        if git("diff", "--cached", "--name-only", cwd=worktree):
            git("commit", "-m", f"Record complete campaign evidence for {tag}", cwd=worktree)
            git("push", URL, "HEAD:main", cwd=worktree)
        print("CAMPAIGN_PUBLISHED", git("rev-parse", "HEAD", cwd=worktree), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--publish", action="store_true", help="Push this compact campaign through a detached worktree")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.tag):
        raise ValueError("Run tag may contain only letters, digits, hyphens and underscores")
    target_root = ROOT / "results" / args.tag
    target_root.mkdir(parents=True, exist_ok=True)
    runs = []
    for directory in sorted((ROOT / "outputs/runs").glob(args.tag + "-*")):
        if not (directory / "config.json").exists():
            continue
        config = json.loads((directory / "config.json").read_text())
        variant = config.get("imagination_termination")
        target = target_root / (config["method"] + ("_" + variant if variant else ""))
        target.mkdir(parents=True, exist_ok=True)
        for name in ("config.json", "runtime.json", "status.json", "failure.json", "evaluation.json"):
            if (directory / name).exists():
                shutil.copy2(directory / name, target / name)
        for path in directory.glob("evaluation_[0-9]*.json"):
            shutil.copy2(path, target / path.name)
        for pattern in ("diagnostics_*.json", "termination_boundary_*.json", "termination_pairing_*.json", "termination_counterfactual_*.json"):
            for path in directory.glob(pattern):
                shutil.copy2(path, target / path.name)
        if (directory / "resume_history").exists():
            shutil.copytree(directory / "resume_history", target / "resume_history", dirs_exist_ok=True)
        rows = []
        if (directory / "metrics.jsonl").exists():
            for line in (directory / "metrics.jsonl").read_text().splitlines(keepends=True):
                if line.endswith("\n"):
                    rows.append(json.loads(line))
            (target / "metrics.jsonl").write_text("".join(json.dumps(row, allow_nan=False) + "\n" for row in rows))
        summary = {"method": config["method"], "run": directory.name, "config_name": config["name"],
                   "relative_results": str(target.relative_to(ROOT)), "execution_directory": str(directory),
                   "last_metrics": rows[-1] if rows else None}
        if variant:
            summary["imagination_termination"] = variant
        summary["evaluation_history"] = [evaluation_summary(json.loads(p.read_text()))
                                         for p in sorted(directory.glob("evaluation_[0-9]*.json"))]
        evaluation = None
        if (directory / "evaluation.json").exists():
            evaluation = json.loads((directory / "evaluation.json").read_text())
            summary.update(evaluation_iteration=evaluation["iteration"], failed_motions=evaluation["failed_motions"],
                           motions=evaluation["motions"], mean_normalized_return=evaluation["mean_normalized_return"],
                           mean_completion_fraction=evaluation["mean_completion_fraction"])
            summary["final_evaluation"] = evaluation_summary(evaluation)
        if (directory / "failure.json").exists():
            summary.update(status="failed", failure=json.loads((directory / "failure.json").read_text())["exception"])
        elif (directory / "status.json").exists():
            status = json.loads((directory / "status.json").read_text())
            summary["status"] = "evaluated" if evaluation and evaluation["iteration"] == status["iteration"] else "training_budget_complete_evaluation_pending"
        else:
            summary["status"] = "running"
        runs.append(summary)
    campaign = {"tag": args.tag, "updated_unix": time.time(), "runs": runs,
                "all_runs_evaluated": len(runs) == 2 and all(r["status"] == "evaluated" for r in runs),
                "both_methods_evaluated": len(runs) == 2 and {r["method"] for r in runs} == {"supermimic", "ppo_sim"} and all(r["status"] == "evaluated" for r in runs),
                "qualification_pass": False,
                "interpretation": "Read config purpose and full-motion results. A completed update loop or evaluation is not a paper-level reproduction pass."}
    (target_root / "summary.json").write_text(json.dumps(campaign, indent=2, ensure_ascii=False) + "\n")
    index_path = ROOT / "results/index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {
        "project": "Independent SuperMimic / G1 / LAFAN1 learning reproduction",
        "preparation": "results/lafan1_g1_preparation", "campaigns": {}}
    index["campaigns"][args.tag] = campaign
    temporary = index_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(index_path)
    print(json.dumps(campaign, ensure_ascii=False), flush=True)
    if args.publish:
        publish_campaign(args.tag, target_root, campaign)


if __name__ == "__main__":
    main()
