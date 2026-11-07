"""P9 job-specific state and fixed-endpoint comparisons."""
import statistics
from pathlib import Path
from p7_results import read, write, success, node_view

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/next_stage_critic_full_scale_protocol.json"


def refresh():
    protocol = read(PROTOCOL)
    result = ROOT / "results" / protocol["campaign"]
    jobs = {name: read(result / "jobs" / name / "summary.json") for name in protocol["jobs"]}
    evidence = result / "evidence/manifest.json"
    acquisition = result / "bones_data/preparation.json"
    summary = {"campaign": protocol["campaign"], "jobs": jobs,
        "status": "completed" if all(j.get("status") == "completed" for j in jobs.values()) and evidence.exists() and read(evidence).get("status") == "published" else "running_or_waiting_for_data",
        "training_started": any(j.get("training_started", False) for j in jobs.values()),
        "training_done": all(j.get("training_done", False) for j in jobs.values()),
        "full_clip_evaluation_done": all(j.get("full_clip_evaluation_done", False) for j in jobs.values()),
        "evidence": read(evidence) if evidence.exists() else {"status": "pending"},
        "bones_preparation": read(acquisition) if acquisition.exists() else {"status": "pending"},
        "publication_lock": protocol["execution"]["publication_lock"],
        "source_worktree": str(ROOT), "backup_status": "awaiting_user_export_not_confirmed",
        "automatic_stage_cleanup": False,
        "handoff": "Continue live tmux; preserve replay/LR. Each training job stops at target or accumulated16h, then formal scoring and Git publication. No P10."}
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
    for job_id in ("lafan_h32_control", "lafan_h32_survival_critic"):
        run = protocol["jobs"][job_id]["run"]
        views[job_id] = {int(p.parent.name.split("_")[-1]): read(p)
            for p in (ROOT / "results" / run / "milestones").glob("*/comparison.json")}
    common = sorted(set(views["lafan_h32_control"]) & set(views["lafan_h32_survival_critic"]))
    comparison = {"common_evaluated_iterations": common,
        "common_nodes": {str(i): {j: views[j][i] for j in views} for i in common},
        "fixed_endpoint": 60000, "prescribed_tail": [58000, 59000, 60000],
        "parent": "H32-51000:37 complete", "historical_anchor": protocol["source"]["preserve_historical_anchors"],
        "interpretation": "Compare fixed endpoint and common update nodes; no best-checkpoint or pooled-success claim."}
    summaries = {j: read(result / "jobs" / j / "summary.json") for j in views}
    if all(s.get("training_done") and s.get("full_clip_evaluation_done") for s in summaries.values()):
        parent = read(ROOT / protocol["source"]["evaluation"])
        scores = {j: read(ROOT / "results" / protocol["jobs"][j]["run"] / "milestones" / f"iteration_{summaries[j]['final_iteration']:07d}" / "evaluation.json") for j in views}
        names = sorted(success(parent) & success(scores["lafan_h32_control"]) & success(scores["lafan_h32_survival_critic"]))
        comparison["common_full_success"] = {"names": names, "count": len(names), "conditional_only": True,
            "metrics": {label: {key: statistics.mean(next(r for r in s["clips"] if r["motion"] == n)[key] for n in names) if names else None
                for key in ("normalized_return", "mean_root_xy_error_m", "mean_root_orientation_error_rad")}
                for label, s in {"parent_H32-51000": parent, **scores}.items()}}
    write(result / "lafan_comparison.json", comparison)
    if "common_full_success" in comparison:
        lines = ["# P9 LAFAN Critic control/survival 固定预算比较", "",
            "两路从同一H32-51000完整恢复，研究变量仅为Critic的存活加权。下表使用各自真实终点；共同更新节点全部保留于lafan_comparison.json。", "",
            "| 分支 | 实际终点 | 全40回报 | 完整成功 | H32-51000父37保持 | 阶段小时 |",
            "|---|---:|---:|---:|---:|---:|"]
        for j in views:
            s = summaries[j]
            i = s["final_iteration"]
            v = views[j][i]
            lines.append(f"| {j} | {i} | {v['mean_normalized_return']:.8f} | {v['completed_motions']}/40 | {len(v['parent_successes_retained'])}/37 | {s['training_snapshot']['stage_wall_seconds']/3700:.4f} |")
        lines += ["", "尾三58000/59000/60000的可用节点、均值与交集见各分支comparison.json；若时限导致终点不同，不能将终点差当相同更新预算效果。",
            "", "共同完整集合的XY/SO3是条件比较；主成绩仍为全40。按全40回报、父37保持、末三及困难技能质量判断；loss下降本身不证明控制收益。",
            "", "BONES迁移有不同数据与初始化成本，状态单列于summary.json。大产物留D57；不自动延长预算或启动P10。"]
        (result / "conclusion.md").write_text("\n".join(lines)+"\n")
    return comparison
