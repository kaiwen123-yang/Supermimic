"""P8 job-specific state and fixed-endpoint comparisons."""
import statistics
from pathlib import Path
from p7_results import read, write, success, node_view

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/next_stage_stability_scale_protocol.json"


def refresh():
    protocol = read(PROTOCOL)
    result = ROOT / "results" / protocol["campaign"]
    jobs = {name: read(result / "jobs" / name / "summary.json") for name in protocol["jobs"]}
    evidence = result / "evidence/manifest.json"
    acquisition = result / "bones_data/acquisition.json"
    summary = {"campaign": protocol["campaign"], "jobs": jobs,
        "status": "completed" if all(j.get("status") == "completed" for j in jobs.values()) and evidence.exists() and read(evidence).get("status") == "published" else "running_or_waiting_for_data",
        "training_started": any(j.get("training_started", False) for j in jobs.values()),
        "training_done": all(j.get("training_done", False) for j in jobs.values()),
        "full_clip_evaluation_done": all(j.get("full_clip_evaluation_done", False) for j in jobs.values()),
        "evidence": read(evidence) if evidence.exists() else {"status": "pending"},
        "bones_acquisition": read(acquisition) if acquisition.exists() else {"status": "pending"},
        "publication_lock": protocol["execution"]["publication_lock"],
        "source_worktree": str(ROOT), "backup_status": "awaiting_user_export_not_confirmed",
        "automatic_stage_cleanup": False,
        "handoff": "Continue live tmux; preserve replay/LR. Each training job stops at target or accumulated16h, then formal scoring and Git publication. No P9."}
    write(result / "summary.json", summary)
    return summary


def index_update(index, summary):
    record = {"status": summary["status"], "training_started": summary["training_started"],
        "training_done": summary["training_done"], "full_clip_evaluation_done": summary["full_clip_evaluation_done"],
        "summary": f"results/{summary['campaign']}/summary.json", "jobs": summary["jobs"],
        "automatic_stage_cleanup": False, "backup_status": "awaiting_user_export_not_confirmed"}
    index.setdefault("campaigns", {}).setdefault(summary["campaign"], {}).update(record)
    index.setdefault("next_stage", {}).update(record, campaign=summary["campaign"])


def compare_lafan(protocol):
    result = ROOT / "results" / protocol["campaign"]
    views = {}
    for job_id in ("lafan_h32", "lafan_h16"):
        run = protocol["jobs"][job_id]["run"]
        views[job_id] = {int(p.parent.name.split("_")[-1]): read(p)
            for p in (ROOT / "results" / run / "milestones").glob("*/comparison.json")}
    common = sorted(set(views["lafan_h32"]) & set(views["lafan_h16"]))
    comparison = {"common_evaluated_iterations": common,
        "common_nodes": {str(i): {j: views[j][i] for j in views} for i in common},
        "fixed_endpoint": 51000, "prescribed_tail": [49000, 50000, 51000],
        "parent": "C42000:36 complete", "historical_anchor": protocol["source"]["historical_anchor"],
        "interpretation": "Compare fixed endpoint and common update nodes; no best-checkpoint or pooled-success claim."}
    summaries = {j: read(result / "jobs" / j / "summary.json") for j in views}
    if all(s.get("training_done") and s.get("full_clip_evaluation_done") for s in summaries.values()):
        parent = read(ROOT / protocol["source"]["evaluation"])
        scores = {j: read(ROOT / "results" / protocol["jobs"][j]["run"] / "milestones" / f"iteration_{summaries[j]['final_iteration']:07d}" / "evaluation.json") for j in views}
        names = sorted(success(parent) & success(scores["lafan_h32"]) & success(scores["lafan_h16"]))
        comparison["common_full_success"] = {"names": names, "count": len(names), "conditional_only": True,
            "metrics": {label: {key: statistics.mean(next(r for r in s["clips"] if r["motion"] == n)[key] for n in names) if names else None
                for key in ("normalized_return", "mean_root_xy_error_m", "mean_root_orientation_error_rad")}
                for label, s in {"parent_C42000": parent, **scores}.items()}}
    write(result / "lafan_comparison.json", comparison)
    return comparison
