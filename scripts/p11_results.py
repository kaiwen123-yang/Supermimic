"""P11 separate job state and paired comparisons at every common scored node."""
import statistics
from pathlib import Path
from p7_results import read, write, success, node_view
from p10_metrics import read_score, aggregate, HARD_IDS

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/next_stage_root_height_protocol.json"


def refresh():
    p = read(PROTOCOL)
    result = ROOT/"results"/p["campaign"]
    jobs = {j:read(result/"jobs"/j/"summary.json") for j in p["jobs"]}
    for name, job in jobs.items():
        run = ROOT/"outputs/runs"/p["jobs"][name]["run"]
        if (run/"metrics.jsonl").exists():
            import json
            with (run/"metrics.jsonl").open() as stream:
                latest = None
                for line in stream:
                    if line.endswith("\n"):
                        latest = json.loads(line)
            if latest is not None:
                job.update(latest_training=latest, observed_training_iteration=latest["iteration"],
                    observed_new_joint_updates=latest["new_joint_updates"],
                    observed_new_wm_only_updates=latest["new_wm_only_updates"],
                    observed_stage_seconds=read(run/"budget.json")["stage_elapsed_seconds"])
                write(result/"jobs"/name/"summary.json", job)
        p["jobs"][name].update(status=job["status"], training_started=job.get("training_started",False),
            training_done=job.get("training_done",False), implementation_status="implemented_and_"+job["status"],
            full_clip_evaluation_done=job.get("full_clip_evaluation_done",False),
            lightweight_results_published=job.get("lightweight_results_published",False))
    evidence_path = result/"evidence/manifest.json"
    evidence = read(evidence_path) if evidence_path.exists() else {"status":"pending"}
    completed = all(j["status"] == "completed" for j in jobs.values()) and evidence["status"] == "all_three_computed"
    summary = {"campaign":p["campaign"], "jobs":jobs, "status":"completed" if completed else "running",
        "training_started":any(j.get("training_started",False) for j in jobs.values()),
        "training_done":all(j.get("training_done",False) for j in jobs.values()),
        "full_clip_evaluation_done":all(j.get("full_clip_evaluation_done",False) for j in jobs.values()),
        "lightweight_results_published":completed, "evidence":evidence,
        "publication_lock":p["execution"]["publication_lock"], "source_worktree":str(ROOT),
        "parent_checkpoint":p["parent"]["checkpoint"], "parent_known_training_seconds":p["parent"]["known_inherited_training_seconds"],
        "backup_status":"awaiting_user_export_not_confirmed", "automatic_stage_cleanup":False,
        "handoff":"Continue existing live tmux/replay/LR. Each job stops at36000 or accumulated20h, then actual endpoint scoring/publication. No P12."}
    p.update(status=summary["status"], training_started=summary["training_started"],
        training_done=summary["training_done"], full_clip_evaluation_done=summary["full_clip_evaluation_done"],
        lightweight_results_published=summary["lightweight_results_published"])
    if completed:
        p["implementation_status"]="implemented_and_completed"
        for path in (ROOT/"README.md", ROOT/"AGENTS.md", ROOT/"docs/P11_ROOT_HEIGHT_CONSISTENCY_PLAN.md"):
            text=path.read_text()
            text=text.replace("P11 根高度与预测垂直速度一致性研究，两路已正式并行运行。",
                "P11 根高度与预测垂直速度一致性研究，训练、评分、固定证据与轻量发布已完成。")
            text=text.replace("P11两路已实施并正式并行运行。","P11两路训练、评分、固定证据与轻量发布已完成。")
            text=text.replace("接续现有sm-p11-residual和sm-p11-velocity-height，不重复启动P10/P11，不重建活跃replay或重置LR。",
                "两路已按各自真实预算终点完成，不重复启动P10/P11或自动追加预算。")
            text=text.replace("## P11实施（两路已正式运行，接续现有tmux）","## P11实施（已完成）")
            text=text.replace("实现与父七窗预测已完成，两路已正式并行训练并完成真实联合更新。",
                "两路训练、实际终点评分、三模型固定七窗预测和轻量发布已完成。")
            path.write_text(text)
        (ROOT/"docs/P11_CODEX_START_PROMPT.md").write_text(
            "# P11 已完成\n\n两路均按9000新增联合更新或累计新阶段20h的先到条件结束，并完成实际终点评分、固定七窗WM证据和轻量发布。"
            f"实际终点、全部节点和结论见[summary](../results/{p['campaign']}/summary.json)与[conclusion](../results/{p['campaign']}/conclusion.md)。"
            "\n\n不重复启动P10/P11，不追加预算。LAFAN既有复现成功保持；大产物留服务器，rolling20和里程碑保护照旧，不自动清理或开始P12。\n")
    write(PROTOCOL,p)
    write(result/"summary.json",summary)
    return summary


def index_update(index, summary):
    record = {k:summary[k] for k in ("status","training_started","training_done","full_clip_evaluation_done","lightweight_results_published","jobs")}
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
    parent_path = ROOT/p["parent"]["evaluation"]
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
    report = {"fixed_target_iteration":36000, "common_evaluated_iterations":common, "nodes":comparisons,
        "prescribed_bones_tail":[30000,33000,36000],
        "interpretation":"Paired fixed-node scores, no best node or pooled success. Hard improvement, general pose quality and LAFAN retention are reported together."}
    write(result/"paired_comparison.json", report)
    summaries = {j:read(result/"jobs"/j/"summary.json") for j in p["jobs"]}
    if all(s.get("training_done") and s.get("full_clip_evaluation_done") for s in summaries.values()):
        endpoints = {j:read(paths[j][s["final_iteration"]]/"comparison.json") for j,s in summaries.items()}
        lines = ["# P11 两路固定预算结果", "",
            "两路同父P10 hard27000完整恢复，均为8192真实环境/8192想象/WM10×4096及1024个固定hard reset环境；唯一变量是root-z残差或同次预测速度梯形积分。", "",
            "| 分支 | 实际终点 | 全BONES R | hard R | 其余BONES R | body orientation贡献 | LAFAN R/完整/起身 | 阶段h |",
            "|---|---:|---:|---:|---:|---:|---|---:|"]
        for j,v in endpoints.items():
            q,lafan=v["bones"]["quality"],v["lafan_retention"]
            lines.append(f"| {j} | {summaries[j]['final_iteration']} | {q['all_clips']['means']['normalized_return']:.8f} | {q['fixed_hard']['means']['normalized_return']:.8f} | {q['other_bones']['means']['normalized_return']:.8f} | {q['all_clips']['reward_components_normalized']['body_orientation']:.8f} | {lafan['mean_normalized_return']:.8f}/{lafan['completed_motions']}/起身{lafan['categories']['fallAndGetUp']['completed']} | {summaries[j]['cost']['stage_wall_seconds']/3600:.4f} |")
        a,b=(endpoints[j] for j in ("full8k_residual_control","full8k_velocity_height"))
        delta={group:b["bones"]["quality"][group]["means"]["normalized_return"]-a["bones"]["quality"][group]["means"]["normalized_return"]
            for group in ("all_clips","fixed_hard","other_bones")}
        lines += ["",f"预测速度高度路减原残差路的终点回报差：全库 {delta['all_clips']:+.8f}，hard {delta['fixed_hard']:+.8f}，其余BONES {delta['other_bones']:+.8f}；LAFAN {b['lafan_retention']['mean_normalized_return']-a['lafan_retention']['mean_normalized_return']:+.8f}。",
            "",f"全部共同评分节点 {common} 保存在paired_comparison.json；共同完整集合的XY/SO3/body/joint、body orientation贡献和hard条件集合分别保留。若实际终点不同，终点差不能解释为相同更新预算的效果。",
            "", "每路的父成功保持、四组困难技能、实际曝光和WM有效窗见节点comparison与hard_exposure；每个分支保留全部规定节点与尾三交集，不选择最佳单点。",
            "", "本阶段是一次父模型和固定预算的模拟研究，真实结果不自动证明收敛、泛化、唯一机制或实机能力。按预算停止，不自动追加或启动P12；大产物留D57，用户备份未确认。"]
        evidence = read(result/"evidence/manifest.json")
        lines += ["", "固定七窗同输入WM比较见evidence/manifest.json及各模型的manifest.json。候选r_z接近零是构造结果；预测准确性以真实z/vz/SO3/joint误差判断，控制收益以上表和各技能正式评分判断。LAFAN达到0.82的既有复现成功保持。",
            "", "| 模型 | 七窗平均绝对z误差 m | 七窗平均绝对vz误差 m/s | SO3误差 rad |",
            "|---|---:|---:|---:|"]
        for label, record in evidence["models"].items():
            avg = record["mean_over_fixed_windows"]
            lines.append(f"| {label} | {avg['z_mae_m']:.8f} | {avg['vz_mae_m_per_s']:.8f} | {avg['root_SO3_mean_rad']:.8f} |")
        (result/"conclusion.md").write_text("\n".join(lines)+"\n")
    return report
