"""One fixed-node official evaluation and lightweight publication under the shared lock."""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

from common import CAMPAIGN, PUBLICATION_LOCK, RUN_NAME, now, write_json


def github(path, method="GET", data=None):
    command = ["gh", "api", f"repos/kaiwen123-yang/Supermimic/{path}", "--method", method]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=None if data is None else json.dumps(data), text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def publish(result_dir: Path, label: str) -> str:
    head = github("git/ref/heads/main")["object"]["sha"]
    base_tree = github(f"git/commits/{head}")["tree"]["sha"]
    files = [path for path in result_dir.rglob("*") if path.suffix in {".json", ".csv", ".md"} and path.is_file()]
    tree = [{"path": f"results/{CAMPAIGN}/{path.relative_to(result_dir).as_posix()}",
             "mode": "100644", "type": "blob", "content": path.read_text()} for path in files]
    created = github("git/trees", "POST", {"base_tree": base_tree, "tree": tree})
    commit = github("git/commits", "POST", {"message": f"Publish O1 official LAFAN40 {label} full evaluation",
                      "tree": created["sha"], "parents": [head]})
    github("git/refs/heads/main", "PATCH", {"sha": commit["sha"], "force": False})
    return commit["sha"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    run_dir = args.workspace / "outputs" / RUN_NAME
    result_dir = args.workspace / "results" / CAMPAIGN
    output = result_dir / "milestones" / args.label
    started = time.monotonic()
    write_json(run_dir / f"evaluation_{args.label}_status.json", {"status": "waiting_for_publication_lock", "queued_at": now()})
    with PUBLICATION_LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        subprocess.run([sys.executable, str(Path(__file__).with_name("evaluate_official.py")),
                        "--workspace", str(args.workspace), "--checkpoint", str(args.checkpoint), "--output", str(output)], check=True)
        current = json.loads((output / "evaluation.json").read_text())
        if current["mean_normalized_return"] >= 0.82:
            write_json(run_dir / "stop_after_success.json", {"checkpoint": str(args.checkpoint),
                       "mean_normalized_return": current["mean_normalized_return"], "evaluation": str(output), "recorded_at": now()})
        evaluations = {path.parent.name: json.loads(path.read_text()) for path in sorted(result_dir.glob("milestones/*/evaluation.json"))}
        common = set.intersection(*(set(item["completed_clip_names"]) for item in evaluations.values()))
        common_quality = {}
        for label in evaluations:
            with (result_dir / "milestones" / label / "per_clip.csv").open() as stream:
                rows = [row for row in csv.DictReader(stream) if row["name"] in common]
            common_quality[label] = {key: sum(float(row[key]) for row in rows) / len(rows)
                                     for key in ["normalized_return", "root_xy_error_m", "root_orientation_error_rad", "relative_body_position_error_m", "relative_body_orientation_error_rad"]} if rows else {}
        progress = json.loads((run_dir / "progress.json").read_text())
        target_reached = any(item["mean_normalized_return"] >= 0.82 for item in evaluations.values())
        summary = {"campaign": CAMPAIGN, "run_name": RUN_NAME, "updated_at": now(),
                   "status": "completed" if args.label == "final" else "training",
                   "latest_training": progress, "evaluations": evaluations,
                   "target_return": 0.82, "target_reached": target_reached,
                   "common_complete_clips": sorted(common), "common_complete_quality": common_quality,
                   "training_finished": args.label == "final", "publication": "included_in_this_commit",
                   "large_artifacts": str(run_dir), "legacy_lafan_success_preserved": True}
        write_json(result_dir / "summary.json", summary)
        lines = ["# O1 official LAFAN40", "", f"Status: {summary['status']}. Updated: {summary['updated_at']}.", "",
                 "| Fixed checkpoint | Mean normalized return | Complete / 40 | Training seconds |", "|---|---:|---:|---:|"]
        for label, item in evaluations.items():
            lines.append(f"| {label} | {item['mean_normalized_return']:.8f} | {item['completed']} / 40 | {item['checkpoint_metadata']['training_seconds']:.1f} |")
        lines += ["", f"Formal R >= 0.82 observed: {target_reached}. All 40 clips, including failures, are in each milestone's per_clip.csv.",
                  "", "The official current-main GenCoord/proprio/history10 baseline uses a fresh seed-0 initialization. Historical paper run config is not claimed recovered. Large weights and logs remain on D57.",
                  "", "This run does not change the previously accepted independent LAFAN1 reproduction result.", ""]
        (result_dir / "README.md").write_text("\n".join(lines))
        try:
            sha = publish(result_dir, args.label)
        except subprocess.CalledProcessError as error:
            write_json(run_dir / f"publication_{args.label}.json", {"status": "failed", "at": now(), "stderr": error.stderr,
                       "scores_saved": str(output), "training_and_evaluation_must_not_be_repeated": True})
            raise
        write_json(run_dir / f"publication_{args.label}.json", {"status": "published", "commit": sha, "at": now(),
                   "queued_evaluation_publication_seconds": time.monotonic() - started})
        write_json(run_dir / f"evaluation_{args.label}_status.json", {"status": "completed_and_published", "at": now(), "commit": sha})
        print(f"O1_PUBLISHED {args.label} {sha}", flush=True)


if __name__ == "__main__":
    main()
