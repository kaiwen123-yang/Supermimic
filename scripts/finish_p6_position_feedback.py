"""P6 arm completion and fixed-node comparison; no rollout beyond formal evaluation."""
import argparse
import fcntl
import json
import statistics
import time
from pathlib import Path

from publish_checkpoint import ROOT, REPO, publish, push_results
from finish_c0_continuation import compare_to_parent
from finish_tracking_campaign import training_summary, write
from position_feedback_metrics import reward_quality

PROTOCOL = ROOT / "configs/next_stage_position_feedback_protocol.json"


def read(path):
    return json.loads(path.read_text())


def success(score):
    return {r["motion"] for r in score["clips"] if not r["failed"]}


def view(parent, score):
    compared = compare_to_parent(parent, score)
    return {"iteration": score["iteration"], "completed_motions": score["completed_motions"],
            "mean_normalized_return": score["mean_normalized_return"],
            "mean_completion_fraction": score["mean_completion_fraction"],
            "actor_root_position_feedback": score.get("actor_root_position_feedback", False),
            "reward_quality": reward_quality(score),
            "parent_success_denominator": len(success(parent)),
            "parent_failure_denominator": len(parent["clips"]) - len(success(parent)),
            **{k: compared[k] for k in ("categories", "parent_successes_retained", "parent_successes_lost", "newly_completed")},
            "completed_motion_names": sorted(success(score)),
            "getups": [r for r in score["clips"] if r["motion"].startswith("fallAndGetUp")],
            "running": [r for r in score["clips"] if r["motion"].startswith("run")]}


def aggregate(protocol, summaries):
    parent = read(ROOT / protocol["parent"]["evaluation"])
    arms = [a["id"] for a in protocol["arms"]]
    nodes = {}
    finals = {}
    for arm in arms:
        run = ROOT / "outputs/runs" / summaries[arm]["run"]
        nodes[arm] = {i: read(run / f"evaluation_{i:07d}/evaluation.json")
                      for i in summaries[arm]["evaluated_iterations"]}
        finals[arm] = nodes[arm][summaries[arm]["final_iteration"]]
    common = sorted(set(nodes[arms[0]]) & set(nodes[arms[1]]))
    tail = protocol["retention"]["predeclared_tail_iterations"]
    available_tail = [i for i in tail if i in common]
    tail_stats = {}
    for arm in arms:
        values = [nodes[arm][i]["mean_normalized_return"] for i in available_tail]
        intersection = set.intersection(*(success(nodes[arm][i]) for i in available_tail)) if available_tail else set()
        tail_stats[arm] = {"available_common_iterations": available_tail,
            "missing_predeclared_iterations": [i for i in tail if i not in nodes[arm]],
            "mean_return_over_available_common_nodes": statistics.mean(values) if values else None,
            "mean_completed_over_available_common_nodes": statistics.mean(nodes[arm][i]["completed_motions"] for i in available_tail) if available_tail else None,
            "return_range_over_available_common_nodes": [min(values), max(values)] if values else None,
            "available_node_success_intersection": sorted(intersection),
            "three_node_success_intersection": sorted(intersection) if available_tail == tail else None,
            "three_node_getup_intersection": sorted(n for n in intersection if n.startswith("fallAndGetUp")) if available_tail == tail else None,
            "parent_successes_in_available_intersection": sorted(intersection & success(parent)),
            "nodes": {str(i): view(parent, nodes[arm][i]) for i in tail if i in nodes[arm]}}
    xy_names = sorted(success(parent) & success(finals[arms[0]]) & success(finals[arms[1]]))
    xy = {}
    for label, score in {"parent24000": parent, **finals}.items():
        rows = {r["motion"]: r for r in score["clips"]}
        xy[label] = {"iteration": score["iteration"], "per_motion_mean_xy_error_m":
            {name: rows[name]["mean_root_xy_error_m"] for name in xy_names}}
        xy[label]["subset_mean_xy_error_m"] = statistics.mean(xy[label]["per_motion_mean_xy_error_m"].values()) if xy_names else None
    a, b = (finals[arm] for arm in arms)
    complete_fixed = all(33000 in nodes[arm] for arm in arms) and available_tail == tail
    qualities = {label: reward_quality(score) for label, score in {"parent24000": parent, **finals}.items()}
    root_rewards = {label: q["mean"]["components"]["global_root_position"]["normalized_contribution"]
                    for label, q in qualities.items()}
    position_improved = bool(xy_names) and all(
        xy[arms[1]]["subset_mean_xy_error_m"] < xy[label]["subset_mean_xy_error_m"] and
        root_rewards[arms[1]] > root_rewards[label] for label in ("parent24000", arms[0]))
    ta, tb = (tail_stats[arm] for arm in arms)
    retention = {label: len(success(score) & success(parent)) for label, score in finals.items()}
    overall_retained = all(b["mean_normalized_return"] >= score["mean_normalized_return"] and
        b["completed_motions"] >= score["completed_motions"] and
        b["mean_completion_fraction"] >= score["mean_completion_fraction"] for score in (parent, a))
    tail_retained = complete_fixed and (
        tb["mean_return_over_available_common_nodes"] >= ta["mean_return_over_available_common_nodes"] and
        tb["mean_completed_over_available_common_nodes"] >= ta["mean_completed_over_available_common_nodes"] and
        len(tb["three_node_success_intersection"]) >= len(ta["three_node_success_intersection"]) and
        retention[arms[1]] >= retention[arms[0]])
    if not complete_fixed:
        decision = "固定33000或预定末三共同节点未齐，报告实际终点及共同进度；保留P5 B24000，不用不等预算宣布位置反馈获胜。"
    elif position_improved and overall_retained and tail_retained:
        decision = "B在共同完整集合的XY和全40根位置奖励均优于父模型与A，总体回报/完成及后段保持也支持反馈支；本次预算下建议采用B。"
    else:
        decision = "位置反馈未同时呈现位置、总体回报/完成和后段保持的一致收益；报告逐项改善与退化，保留P5 B24000作为可用基线，不自动追加实验。"
    return {"parent_iteration": 24000, "parent_success_count": len(success(parent)), "parent_failure_count": len(parent["clips"])-len(success(parent)),
        "parent_scores": view(parent, parent), "common_iterations": common,
        "all_milestones": {arm: {str(i): view(parent, score) for i, score in nodes[arm].items()} for arm in arms},
        "fixed_33000": {arm: view(parent, nodes[arm][33000]) if 33000 in nodes[arm] else None for arm in arms},
        "last_common_iteration": common[-1] if common else None,
        "last_common_scores": {arm: view(parent, nodes[arm][common[-1]]) for arm in arms} if common else {},
        "actual_finals": {arm: view(parent, finals[arm]) for arm in arms}, "tail": tail_stats,
        "reward_quality": qualities,
        "position_feedback_assessment": {"common_xy_and_root_reward_improved_vs_parent_and_control": position_improved,
            "overall_return_completion_not_lower_than_parent_and_control": overall_retained,
            "tail_and_retention_not_lower_than_control": tail_retained,
            "B_minus_A": {"mean_return": b["mean_normalized_return"]-a["mean_normalized_return"],
                "mean_completion": b["mean_completion_fraction"]-a["mean_completion_fraction"],
                "completed_motions": b["completed_motions"]-a["completed_motions"],
                "parent_successes_retained": retention[arms[1]]-retention[arms[0]],
                "root_position_contribution": root_rewards[arms[1]]-root_rewards[arms[0]],
                "common_set_xy_m": xy[arms[1]]["subset_mean_xy_error_m"]-xy[arms[0]]["subset_mean_xy_error_m"] if xy_names else None}},
        "xy_common_full_success": {"motion_names": xy_names, "count": len(xy_names), "scores": xy,
            "scope": "Same full motions completed by parent B24000 and both actual finals; this subset is not all 40 motions."},
        "decision": decision, "next_step": "结合奖励分项和实际失败窗口解释取舍；本次不自动扩预算或启动P7。",
        "interpretation": "One seed and one parent; tail nodes are not independent seeds. Position feedback is a project hypothesis, not the author's undisclosed goal. No per-motion checkpoint splicing. A single crossing of 0.82 does not reproduce paper efficiency, scale or hardware results."}



def write_report(result, comparison, summaries):
    lines = ["# P6 当前相对根位置反馈 A/B 结果", "", comparison["decision"], "",
             "| 组别 | 实际终点 | 新联合更新 | 阶段小时 | 完整数 | 回报 | 起身 | 跑步 | 父成功保持 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, v in comparison["actual_finals"].items():
        s = summaries[arm]["training_snapshot"]
        lines.append(f"| {arm} | {v['iteration']} | {s['new_joint_updates']} | {s['stage_wall_seconds']/3600:.3f} | {v['completed_motions']}/40 | {v['mean_normalized_return']:.8f} | {v['categories']['fallAndGetUp']['completed']}/6 | {v['categories']['run']['completed']}/4 | {len(v['parent_successes_retained'])}/{v['parent_success_denominator']} |")
    for arm, v in comparison["actual_finals"].items():
        tail = comparison["tail"][arm]
        lines += ["", f"## {arm}", "", "六条起身：" + "；".join(f"{r['motion']}：{'完整' if not r['failed'] else r['reason']}，{r['execution_seconds']:.2f}s" for r in v["getups"]),
            "", "四条跑步：" + "；".join(f"{r['motion']}：{'完整' if not r['failed'] else r['reason']}，回报{r['normalized_return']:.6f}" for r in v["running"]),
            "", "父成功退化：" + (", ".join(v["parent_successes_lost"]) or "无"),
            "", "新增成功：" + (", ".join(v["newly_completed"]) or "无"),
            "", f"末三共同节点：{tail['available_common_iterations']}；回报均值/范围：{tail['mean_return_over_available_common_nodes']} / {tail['return_range_over_available_common_nodes']}。",
            "", f"三节点都成功的动作：{tail['three_node_success_intersection']}；其中起身：{tail['three_node_getup_intersection']}。",
            "", f"缺失预定节点：{tail['missing_predeclared_iterations']}。"]
    xy = comparison["xy_common_full_success"]
    lines += ["", "## 同集合 XY", "", f"共同完整成功集合共{xy['count']}条：" + ", ".join(xy["motion_names"]), ""]
    lines += [f"- {label}（{v['iteration']}）：平均XY误差 {v['subset_mean_xy_error_m']} m。" for label, v in xy["scores"].items()]
    lines += ["", "逐动作XY、所有节点评分和动作身份见 comparison.json；区间训练统计与原始产物路径见各arm目录。", "",
              "最终失败事件来自各arm的failure_windows.json；P5 A24000成功起身轨迹仍保留原服务器位置作为解释参考。", "",
              "这些是40条训练动作的单父版本、单seed结果，末三节点不是独立重复。位置反馈是本项目假设，不是作者未公开实现；一次超过0.82不等于复现整篇论文。", "", comparison["next_step"], "",
              "大权重、逐轮日志、原始评分轨迹和缓存保留服务器，待用户备份；备份未确认，不自动删除。"]
    lines += ["", "## 全40动作奖励贡献与质量缺口", "",
        "各动作按完整参考时长归一后等权平均；1−R=(1−C)+(C−R)。", "",
        "| 策略 | 回报R | 完成C | 未执行尾部1−C | 执行段质量C−R |", "|---|---:|---:|---:|---:|"]
    for label, quality in comparison["reward_quality"].items():
        q = quality["mean"]
        lines.append(f"| {label} | {q['mean_return']:.8f} | {q['completion_fraction']:.8f} | {q['missing_tail_gap']:.8f} | {q['executed_quality_gap']:.8f} |")
    lines += ["", "| 策略 | 奖励项 | 实得贡献 | 执行段可得上限 | 执行段缺口 |", "|---|---|---:|---:|---:|"]
    for label, quality in comparison["reward_quality"].items():
        for name, part in quality["mean"]["components"].items():
            lines.append(f"| {label} | {name} | {part['normalized_contribution']:.8f} | {part['executed_available_maximum']:.8f} | {part['executed_quality_gap']:.8f} |")
    lines += ["", "原始全40评分及逐动作分项保留；不同完成长度的全40分项需结合共同完整集合XY解读。"]
    (result / "conclusion.md").write_text("\n".join(lines) + "\n")


def finish(arm):
    protocol = read(PROTOCOL)
    spec = next(a for a in protocol["arms"] if a["id"] == arm)
    run = ROOT / "outputs/runs" / spec["run"]
    status = read(run / "status.json")
    final = status["iteration"]
    nodes = sorted({i for i in protocol["evaluation"]["iterations"] if i <= final} | {final})
    publications = [publish(run.name, i, final=i == final) for i in nodes]
    with (ROOT / "work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = ROOT / "results" / protocol["campaign"]
        arm_dir = result / "arms" / arm
        summary = read(arm_dir / "summary.json")
        final_result = ROOT / "results" / run.name / "milestones" / f"iteration_{final:07d}"
        write(arm_dir / "failure_windows.json", read(final_result / "failure_windows.json"))
        training = training_summary(run)
        training["interpretation"] = "Actual category sampling and global WM error; no new same-action model prediction or category-specific WM error."
        write(arm_dir / "training.json", training)
        summary.update(status="publishing", training_done=True, full_clip_evaluation_done=True,
            lightweight_results_published=False, training_snapshot=status, final_iteration=final,
            evaluated_iterations=nodes, previous_elapsed_seconds=read(run / "runtime.json")["previous_elapsed_seconds"],
            final_scores={k:v for k,v in read(run / f"evaluation_{final:07d}/evaluation.json").items() if k not in ("clips", "data_definition")},
            evaluation_wall_seconds=sum(read(run / f"evaluation_{i:07d}/evaluation.json")["wall_seconds"] for i in nodes),
            publications=[{"iteration":p["iteration"],"results_commit":p["results_commit"],"url":p["result_url"]} for p in publications])
        write(arm_dir / "summary.json", summary)
        summaries = {a["id"]: read(result / "arms" / a["id"] / "summary.json") for a in protocol["arms"]}
        both = all(s.get("full_clip_evaluation_done", False) for s in summaries.values())
        campaign = read(result / "summary.json")
        campaign.update(status="publishing" if both else "running", arms=summaries,
                        training_done=all(s.get("training_done", False) for s in summaries.values()),
                        full_clip_evaluation_done=both, lightweight_results_published=False)
        if both:
            comparison = aggregate(protocol, summaries)
            write(result / "comparison.json", comparison)
            write_report(result, comparison, summaries)
            campaign["decision"] = comparison["decision"]
        write(result / "summary.json", campaign)

        def update(index):
            record = {"status": campaign["status"], "summary": str((result / "summary.json").relative_to(ROOT)),
                      "arms": {key:{k:s[k] for k in ("run", "status", "training_done", "full_clip_evaluation_done", "lightweight_results_published")}
                               for key,s in summaries.items()},
                      "backup_status":"awaiting_user_export_not_confirmed", "automatic_stage_cleanup":False}
            index["campaigns"][protocol["campaign"]].update(record)
            index["next_stage"].update(record, campaign=protocol["campaign"], training_started=True)

        commit = push_results("p6-" + arm + "-completed", [result.relative_to(ROOT)], update)
        summary.update(status="completed", lightweight_results_published=True, results_commit=commit, completed_unix=time.time())
        summaries[arm] = summary
        write(arm_dir / "summary.json", summary)
        campaign.update(status="completed" if both else "running", arms=summaries,
                        lightweight_results_published=both, results_commit=commit)
        write(result / "summary.json", campaign)
        protocol = read(PROTOCOL)
        protocol["status"] = campaign["status"]
        protocol["execution"].update(status=campaign["status"], training_done=campaign["training_done"],
            formal_evaluation_done=both, key_results_published=both, arms={a:s["status"] for a,s in summaries.items()})
        write(PROTOCOL, protocol)
        paths = [result.relative_to(ROOT), PROTOCOL.relative_to(ROOT)]
        if both:
            readme = ROOT / "README.md"
            lines = readme.read_text().splitlines()
            for i,line in enumerate(lines):
                if line.startswith("> **当前入口：") and "P6" in line:
                    lines[i] = f"> **当前入口：P6已完成训练、正式评分和关键结果发布。** {comparison['decision']} 见[最终分析](results/{protocol['campaign']}/conclusion.md)和[结果索引](results/{protocol['campaign']}/summary.json)。不自动追加训练。"
                    break
            readme.write_text("\n".join(lines) + "\n")
            plan = ROOT / "docs/P6_POSITION_FEEDBACK_PLAN.md"
            lines = plan.read_text().splitlines()
            for i,line in enumerate(lines):
                if line.startswith("状态："):
                    lines[i] = f"状态：**训练、正式评分和关键结果已完成。** 见 [最终分析](../results/{protocol['campaign']}/conclusion.md)。"
                    break
            plan.write_text("\n".join(lines) + "\n")
            agents = ROOT / "AGENTS.md"
            lines = agents.read_text().splitlines()
            for i, line in enumerate(lines):
                if line.startswith("- 当前入口是 docs/P6_POSITION_FEEDBACK_PLAN.md"):
                    lines[i] = f"- P6已完成训练、正式评分和轻量发布；真实终点与结论见results/{protocol['campaign']}/summary.json和conclusion.md。不重复启动或自动扩预算/P7。"
                elif line.startswith("## P6实施"):
                    lines[i] = "## P6实施（本段已完成，保留执行约定）"
            agents.write_text("\n".join(lines) + "\n")
            prompt = ROOT / "docs/NEXT_STAGE_START_PROMPT.md"
            lines = prompt.read_text().splitlines()
            lines[2] = f"P6已完成本段训练、正式评分和轻量发布。先读取results/{protocol['campaign']}/summary.json和conclusion.md；以下为本段历史启动词，不重复执行，不自动开启下一阶段。"
            prompt.write_text("\n".join(lines) + "\n")
            paths += [Path("README.md"), Path("docs/P6_POSITION_FEEDBACK_PLAN.md"), Path("AGENTS.md"), Path("docs/NEXT_STAGE_START_PROMPT.md")]
        push_results("p6-" + arm + "-publication-confirmed", paths, update)
        print("P6_ARM_COMPLETE", arm, final, campaign["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("arm", choices=("no_position_feedback", "root_position_feedback"))
    finish(p.parse_args().arm)
