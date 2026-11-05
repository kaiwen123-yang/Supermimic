"""Compact, separate result views for the two prescribed P7 research jobs."""
import json
from pathlib import Path
from position_feedback_metrics import reward_quality

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/next_stage_reproduction_protocol.json"


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n")


def success(score):
    return {r["motion"] for r in score["clips"] if not r["failed"]}


def node_view(parent, score, evaluation_path):
    result = {k:score[k] for k in ("iteration","completed_motions","mean_normalized_return",
        "mean_completion_fraction","mean_tracking_coverage")}
    result.update(evaluation=evaluation_path, reward_quality_mean=reward_quality(score)["mean"],
        completed_motion_names=sorted(success(score)),
        failed_motions=[{k:r[k] for k in ("motion","reason","execution_seconds","completion_fraction","normalized_return")}
                        for r in score["clips"] if r["failed"]],
        categories={prefix:{"total":sum(r["motion"].startswith(prefix) for r in score["clips"]),
            "completed":sum(r["motion"].startswith(prefix) and not r["failed"] for r in score["clips"])}
            for prefix in ("fallAndGetUp","run")},
        running_and_getups=[{k:r[k] for k in ("motion","failed","reason","execution_seconds","normalized_return")}
                            for r in score["clips"] if r["motion"].startswith(("fallAndGetUp","run"))])
    if parent is not None:
        retained=success(parent)&success(score)
        result.update(parent_iteration=parent["iteration"],parent_success_denominator=len(success(parent)),
            parent_failure_denominator=len(parent["clips"])-len(success(parent)),
            parent_successes_retained=sorted(retained),parent_successes_lost=sorted(success(parent)-success(score)),
            newly_completed=sorted(success(score)-success(parent)),
            parent_failure_outcomes=[{k:r[k] for k in ("motion","failed","reason","execution_seconds","normalized_return")}
                for r in score["clips"] if r["motion"] not in success(parent)])
    return result


def refresh_campaign(protocol):
    result=ROOT/"results"/protocol["campaign"]
    campaign=read(result/"summary.json")
    jobs={j["id"]:read(result/"jobs"/j["id"]/"summary.json") for j in protocol["jobs"]}
    all_done=all(j.get("training_done",False) for j in jobs.values())
    all_evaluated=all(j.get("full_clip_evaluation_done",False) for j in jobs.values())
    published=all(j.get("lightweight_results_published",False) for j in jobs.values())
    evidence_path=ROOT/protocol["evidence_backfill"]["output_root"]/"manifest.json"
    evidence=read(evidence_path) if evidence_path.exists() else {"status":"pending"}
    complete=all_evaluated and published and evidence["status"]=="published"
    campaign.update(jobs=jobs,status="completed" if complete else "running",training_done=all_done,
        full_clip_evaluation_done=all_evaluated,lightweight_results_published=published,
        evidence_backfill={"status":evidence["status"],"manifest":str(evidence_path.relative_to(ROOT))})
    write(result/"summary.json",campaign)
    return campaign


def update_index(index, campaign):
    record={k:campaign[k] for k in ("status","training_started","training_done",
        "full_clip_evaluation_done","lightweight_results_published","jobs","evidence_backfill")}
    record.update(summary=f"results/{campaign['campaign']}/summary.json",
                  backup_status="awaiting_user_export_not_confirmed",automatic_stage_cleanup=False)
    index.setdefault("campaigns",{}).setdefault(campaign["campaign"],{}).update(record)
    index["next_stage"].update(record,campaign=campaign["campaign"])
