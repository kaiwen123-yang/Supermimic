"""Copy compact actual run evidence to Git-facing results; keep weights on D57."""
from pathlib import Path
import argparse
import json
import re
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
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
        target = target_root / config["method"]
        target.mkdir(parents=True, exist_ok=True)
        for name in ("config.json", "runtime.json", "status.json", "failure.json", "evaluation.json"):
            if (directory / name).exists():
                shutil.copy2(directory / name, target / name)
        for path in directory.glob("evaluation_[0-9]*.json"):
            shutil.copy2(path, target / path.name)
        rows = []
        if (directory / "metrics.jsonl").exists():
            for line in (directory / "metrics.jsonl").read_text().splitlines(keepends=True):
                if line.endswith("\n"):
                    rows.append(json.loads(line))
            (target / "metrics.jsonl").write_text("".join(json.dumps(row, allow_nan=False) + "\n" for row in rows))
        summary = {"method": config["method"], "run": directory.name, "config_name": config["name"],
                   "relative_results": str(target.relative_to(ROOT)), "execution_directory": str(directory),
                   "last_metrics": rows[-1] if rows else None}
        if (directory / "evaluation.json").exists():
            evaluation = json.loads((directory / "evaluation.json").read_text())
            summary.update(status="evaluated", failed_motions=evaluation["failed_motions"],
                           motions=evaluation["motions"], mean_normalized_return=evaluation["mean_normalized_return"],
                           mean_completion_fraction=evaluation["mean_completion_fraction"])
        elif (directory / "failure.json").exists():
            summary.update(status="failed", failure=json.loads((directory / "failure.json").read_text())["exception"])
        elif (directory / "status.json").exists():
            summary["status"] = "training_budget_complete_evaluation_pending"
        else:
            summary["status"] = "running"
        runs.append(summary)
    campaign = {"tag": args.tag, "updated_unix": time.time(), "runs": runs,
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


if __name__ == "__main__":
    main()
