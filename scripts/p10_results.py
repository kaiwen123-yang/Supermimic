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
    summaries = {j:read(result/"jobs"/j/"summary.json") for j in p["jobs"]}
    if all(s.get("training_done") and s.get("full_clip_evaluation_done") for s in summaries.values()):
        endpoints = {j:read(paths[j][s["final_iteration"]]/"comparison.json") for j,s in summaries.items()}
        lines = ["# P10 两路固定预算结果", "",
            "两路同父P9 full9000完整恢复，均为8192真实环境/8192想象/WM10×4096；差异是1024个固定hard reset环境。", "",
            "| 分支 | 实际终点 | 全BONES R | hard R | 其余BONES R | body orientation贡献 | LAFAN R/完整/起身 | 阶段h |",
            "|---|---:|---:|---:|---:|---:|---|---:|"]
        for j,v in endpoints.items():
            q,lafan=v["bones"]["quality"],v["lafan_retention"]
            lines.append(f"| {j} | {summaries[j]['final_iteration']} | {q['all_clips']['means']['normalized_return']:.8f} | {q['fixed_hard']['means']['normalized_return']:.8f} | {q['other_bones']['means']['normalized_return']:.8f} | {q['all_clips']['reward_components_normalized']['body_orientation']:.8f} | {lafan['mean_normalized_return']:.8f}/{lafan['completed_motions']}/起身{lafan['categories']['fallAndGetUp']['completed']} | {summaries[j]['cost']['stage_wall_seconds']/3600:.4f} |")
        a,b=(endpoints[j] for j in ("full8k_control","full8k_hard_practice"))
        delta={group:b["bones"]["quality"][group]["means"]["normalized_return"]-a["bones"]["quality"][group]["means"]["normalized_return"]
            for group in ("all_clips","fixed_hard","other_bones")}
        lines += ["",f"困难练习路减控制路的终点回报差：全库 {delta['all_clips']:+.8f}，hard {delta['fixed_hard']:+.8f}，其余BONES {delta['other_bones']:+.8f}；LAFAN {b['lafan_retention']['mean_normalized_return']-a['lafan_retention']['mean_normalized_return']:+.8f}。",
            "",f"全部共同评分节点 {common} 保存在paired_comparison.json；共同完整集合的XY/SO3/body/joint、body orientation贡献和hard条件集合分别保留。若实际终点不同，终点差不能解释为相同更新预算的效果。",
            "", "每路的父成功保持、四组困难技能、实际曝光和WM有效窗见节点comparison与hard_exposure；每个分支保留全部规定节点与尾三交集，不选择最佳单点。",
            "", "本阶段是一次父模型和固定预算的模拟研究，真实结果不自动证明收敛、泛化、唯一机制或实机能力。按预算停止，不自动追加或启动P11；大产物留D57，用户备份未确认。"]
        (result/"conclusion.md").write_text("\n".join(lines)+"\n")
    return report
