"""P8 formal scoring and compact Git publication under the existing shared lock."""
import argparse
import fcntl
import shutil
import subprocess
import sys
import time
from pathlib import Path
from p8_results import ROOT, PROTOCOL, read, write, refresh, index_update, node_view, compare_lafan
from publish_checkpoint import push_results
from finish_tracking_campaign import training_summary


def publish(run_name, iteration, final=False):
    protocol = read(PROTOCOL)
    run = ROOT / "outputs/runs" / run_name
    cfg = read(run / "config.json")
    job_id = cfg["job"]
    job = protocol["jobs"][job_id]
    final = final or iteration == job["target_iteration"]
    campaign_dir = ROOT / "results" / protocol["campaign"]
    jobdir = campaign_dir / "jobs" / job_id
    result = ROOT / "results" / run_name / "milestones" / f"iteration_{iteration:07d}"
    pubdir = ROOT / "outputs/publications" / f"sm-{run_name}-i{iteration:07d}"
    pubdir.mkdir(parents=True, exist_ok=True)
    with Path(protocol["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (pubdir / "publication.json").exists() and read(pubdir / "publication.json").get("status") == "published":
            return read(pubdir / "publication.json")
        evaluation_dir = run / f"evaluation_{iteration:07d}"
        checkpoint = run / f"checkpoint_{iteration:07d}.pt"
        if not (evaluation_dir / "evaluation.json").exists():
            script = "evaluate.py" if job_id.startswith("lafan") else "evaluate_bones.py"
            args = [sys.executable, "-u", str(ROOT / "scripts" / script), str(checkpoint)]
            if final and not job_id.startswith("lafan"):
                args.append("--failure-tails")
            with (pubdir / "evaluation.log").open("a") as log:
                subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        score = read(evaluation_dir / "evaluation.json")
        result.mkdir(parents=True, exist_ok=True)
        for name in ("config.json", "runtime.json"):
            shutil.copy2(run / name, result / name)
        shutil.copy2(evaluation_dir / "evaluation.json", result / "evaluation.json")
        parent_path = ROOT / protocol["source"]["evaluation"] if job_id.startswith("lafan") else ROOT / "results" / run_name / "milestones/iteration_0000000/evaluation.json"
        parent = read(parent_path) if iteration > 0 else None
        comparison = node_view(parent, score, str((result / "evaluation.json").relative_to(ROOT)))
        comparison["motions"] = score["motions"]
        if job_id == "bones40_transfer_h32":
            comparison["categories"] = score["categories"]
            comparison.pop("running_and_getups")
        comparison["interpretation"] = "Full fixed-set equal-clip score; actual parent data definition. No best-node selection."
        write(result / "comparison.json", comparison)
        if iteration > job["start_iteration"]:
            first = max(job["start_iteration"] + 1, ((iteration-1)//cfg["publish_every_iterations"])*cfg["publish_every_iterations"] + 1)
            training = training_summary(run, first, iteration)
            write(result / "training.json", training)
            for block in range(((first-1)//1000+1)*1000, ((iteration-1)//1000+1)*1000+1, 1000):
                for suffix in ("json", "npz"):
                    destination = f"selected_rollouts.{suffix}" if cfg["publish_every_iterations"] == 1000 else f"selected_rollouts_{block:07d}.{suffix}"
                    shutil.copy2(run / "training_evidence" / f"interval_{block:07d}.{suffix}", result / destination)
        summary = read(jobdir / "summary.json")
        runtime = read(run / "runtime.json")
        summary.update(training_started=(run / "metrics.jsonl").exists(), pid=runtime["pid"],
            initialization=runtime["initialization"])
        if not summary.get("training_done"):
            summary["status"] = "running"
        if iteration >= summary.get("latest_evaluated_iteration", -1):
            summary.update(latest_evaluated_iteration=iteration, latest_evaluation={key: score[key] for key in
                ("motions", "completed_motions", "mean_normalized_return", "mean_completion_fraction")},
                latest_parent_successes_retained=len(comparison.get("parent_successes_retained", [])),
                server_artifacts={"run_directory": str(run), "checkpoint": str(checkpoint),
                    "evaluation": str(evaluation_dir), "data_directory": cfg["data_directory"],
                    "source_checkpoint": protocol["source"]["checkpoint"], "backup_status": "awaiting_user_export_not_confirmed"})
        write(jobdir / "summary.json", summary)
        compare_lafan(protocol)
        campaign = refresh()
        status = {"status": "publishing", "run": run_name, "iteration": iteration, "final": final,
            "result_url": f"https://github.com/kaiwen123-yang/Supermimic/tree/main/{result.relative_to(ROOT)}",
            "bulk_artifacts": "retained_on_server", "github_release": False}
        write(result / "publication.json", status)
        commit = push_results(f"p8-{job_id}-i{iteration:07d}",
            [result.relative_to(ROOT), campaign_dir.relative_to(ROOT)], lambda index: index_update(index, campaign))
        status.update(status="published", results_commit=commit, completed_unix=time.time())
        write(pubdir / "publication.json", status)
        write(result / "publication.json", status)
        print("P8_NODE_PUBLISHED", job_id, iteration, commit, flush=True)
        return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("iteration", type=int)
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    publish(args.run, args.iteration, args.final)
