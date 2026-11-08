"""P10 separate job state and paired comparisons at every common scored node."""
import statistics
from pathlib import Path
from p7_results import read, write, success, node_view
from p10_metrics import read_score, aggregate, HARD_IDS

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/next_stage_8k_hard_practice_protocol.json"


def refresh():
    p = read(PROTOCOL)
    result = ROOT/"results"/p["campaign"]
    jobs = {j:read(result/"jobs"/j/"summary.json") for j in p["jobs"]}
    evidence_path = result/"evidence/manifest.json"
    evidence = read(evidence_path) if evidence_path.exists() else {"status":"pending"}
    completed = all(j["status"] == "completed" for j in jobs.values()) and evidence["status"] == "published"
    summary = {"campaign":p["campaign"], "jobs":jobs, "status":"completed" if completed else "running",
        "training_started":any(j.get("training_started",False) for j in jobs.values()),
        "training_done":all(j.get("training_done",False) for j in jobs.values()),
        "full_clip_evaluation_done":all(j.get("full_clip_evaluation_done",False) for j in jobs.values()),
        "lightweight_results_published":completed, "evidence":evidence,
        "publication_lock":p["execution"]["publication_lock"], "source_worktree":str(ROOT),
        "parent_checkpoint":p["source"]["checkpoint"], "parent_known_training_seconds":p["source"]["total_known_training_seconds"],
        "backup_status":"awaiting_user_export_not_confirmed", "automatic_stage_cleanup":False,
        "handoff":"Continue existing live tmux/replay/LR. Each job stops at27000 or accumulated40h, then actual endpoint scoring/publication. No P11."}
    write(result/"summary.json",summary)
    return summary


def index_update(index, summary):
    record = {k:summary[k] for k in ("status","training_started","training_done","full_clip_evaluation_done","jobs")}
    record.update(summary=f"results/{summary['campaign']}/summary.json", automatic_stage_cleanup=False,
        backup_status="awaiting_user_export_not_confirmed")
    index.setdefault("campaigns",{}).setdefault(summary["campaign"],{}).update(record)
    index.setdefault("next_stage",{}).update(record,campaign=summary["campaign"])


def paired_comparisons():
    p = read(PROTOCOL)
    result = ROOT/"results"/p["campaign"]
    paths = {j:{int(d.name.split("_")[-1]):d for d in (ROOT/"results"/v["run"]/"milestones").glob("iteration_*")
        if (d/"comparison.json").exists()} for j,v in p["jobs"].items()}
    common = sorted(set.intersection(*(set(v) for v in paths.values())))
    parent_path = ROOT/p["source"]["evaluation"]
    parent = None
    comparisons = {}
    for i in common:
        views = {j:read(paths[j][i]/"comparison.json") for j in paths}
        entry = {"jobs":views}
        if all((paths[j][i]/"evaluation.json").exists() for j in paths):
            if parent is None:
                parent = read_score(parent_path)
            scores = {j:read_score(paths[j][i]/"evaluation.json") for j in paths}
            names = success(parent).intersection(*(success(s) for s in scores.values()))
            entry["parent_and_both_common_complete"] = {"count":len(names), "conditional_only":True,
                "quality":{j:aggregate([r for r in s["clips"] if r["motion"] in names]) for j,s in {"parent":parent,**scores}.items()},
                "fixed_hard_quality":{j:aggregate([r for r in s["clips"] if r["motion"] in names and r["source_clip_id"] in HARD_IDS])
                    for j,s in {"parent":parent,**scores}.items()}}
        retention = {j:read(paths[j][i]/"lafan_retention.json") for j in paths}
        parent_lafan = read(parent_path.parent/"lafan_retention.json")
        names = success(parent_lafan).intersection(*(success(s) for s in retention.values()))
        entry["lafan_parent_and_both_common_complete"] = {"names":sorted(names), "conditional_only":True,
            "quality":{j:aggregate([r for r in s["clips"] if r["motion"] in names]) for j,s in {"parent":parent_lafan,**retention}.items()}}
        comparisons[str(i)] = entry
    report = {"fixed_target_iteration":27000, "common_evaluated_iterations":common, "nodes":comparisons,
        "prescribed_bones_tail":[15000,21000,27000],
        "interpretation":"Paired fixed-node scores, no best node or pooled success. Hard improvement, general pose quality and LAFAN retention are reported together."}
    write(result/"paired_comparison.json", report)
    return report
