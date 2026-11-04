"""P5 arm completion and fixed-node comparison; no rollout beyond formal evaluation."""
import argparse
import fcntl
import json
import statistics
import time
from pathlib import Path

from publish_checkpoint import ROOT, REPO, publish, push_results
from finish_c0_continuation import compare_to_parent
from finish_tracking_campaign import training_summary, write

PROTOCOL = ROOT / "configs/next_stage_stability_protocol.json"


def read(path):
    return json.loads(path.read_text())


def success(score):
    return {r["motion"] for r in score["clips"] if not r["failed"]}


def view(parent, score):
    compared = compare_to_parent(parent, score)
    return {"iteration": score["iteration"], "completed_motions": score["completed_motions"],
            "mean_normalized_return": score["mean_normalized_return"],
            "mean_completion_fraction": score["mean_completion_fraction"],
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
    for label, score in {"parent18000": parent, **finals}.items():
        rows = {r["motion"]: r for r in score["clips"]}
        xy[label] = {"iteration": score["iteration"], "per_motion_mean_xy_error_m":
            {name: rows[name]["mean_root_xy_error_m"] for name in xy_names}}
        xy[label]["subset_mean_xy_error_m"] = statistics.mean(xy[label]["per_motion_mean_xy_error_m"].values()) if xy_names else None
    a, b = (finals[arm] for arm in arms)
    complete_fixed = all(24000 in nodes[arm] for arm in arms) and available_tail == tail
    if not complete_fixed:
        decision = "固定24000或末三共同节点缺失，报告实际终点和已有共同节点；保持18000可用基线，不用不等预算宣布半Actor LR胜出。"
    elif all(s["mean_normalized_return"] <= parent["mean_normalized_return"] and
             s["completed_motions"] <= parent["completed_motions"] and
             (s["mean_normalized_return"] < parent["mean_normalized_return"] or s["completed_motions"] < parent["completed_motions"]) for s in (a, b)):
        decision = "两支最终回报和完整数均未超过18000且各有退化，保留C0-18000可用基线，依据实际退化动作选择后续问题。"
    else:
        ta, tb = (tail_stats[arm] for arm in arms)
        b_not_worse = (b["mean_normalized_return"] >= a["mean_normalized_return"] and
            b["completed_motions"] >= a["completed_motions"] and
            tb["mean_return_over_available_common_nodes"] >= ta["mean_return_over_available_common_nodes"] and
            tb["mean_completed_over_available_common_nodes"] >= ta["mean_completed_over_available_common_nodes"])
        retention_better = (len(tb["three_node_success_intersection"]) > len(ta["three_node_success_intersection"]) and
            len(success(b) & success(parent)) >= len(success(a) & success(parent)) and
            len(tb["parent_successes_in_available_intersection"]) >= len(ta["parent_successes_in_available_intersection"]))
        decision = ("B在固定终点回报/完整数和末三节点覆盖不低于A，同时成功交集与父动作保持更好；本次预算下建议选B。" if b_not_worse and retention_better else
                    "B未同时满足后段回报/覆盖不低于A且保持性改善的选择条件；保留A作为原设置主线，并报告逐项取舍。")
    return {"parent_iteration": 18000, "common_iterations": common,
        "all_milestones": {arm: {str(i): view(parent, s) for i, s in nodes[arm].items()} for arm in arms},
        "fixed_24000": {arm: view(parent, nodes[arm][24000]) if 24000 in nodes[arm] else None for arm in arms},
        "actual_finals": {arm: view(parent, finals[arm]) for arm in arms}, "tail": tail_stats,
        "xy_common_full_success": {"motion_names": xy_names, "count": len(xy_names), "scores": xy,
            "scope": "Same full motions completed by parent18000 and both actual finals; this subset is not all 40 motions."},
        "decision": decision, "next_step": "先阅读退化动作和真实失败窗口，再决定一个具体问题；本次不自动启动新实验。",
        "interpretation": "One seed and one parent; tail nodes are not independent seeds. Half Actor LR remains an optimization hypothesis, not a proven root cause. No per-motion checkpoint splicing."}


def write_report(result, comparison, summaries):
    lines = ["# P5 A/B 结果", "", comparison["decision"], "",
             "| 组别 | 实际终点 | 新联合更新 | 阶段小时 | 完整数 | 回报 | 起身 | 跑步 | 父32保持 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, v in comparison["actual_finals"].items():
        s = summaries[arm]["training_snapshot"]
        lines.append(f"| {arm} | {v['iteration']} | {s['new_joint_updates']} | {s['stage_wall_seconds']/3600:.3f} | {v['completed_motions']}/40 | {v['mean_normalized_return']:.8f} | {v['categories']['fallAndGetUp']['completed']}/6 | {v['categories']['run']['completed']}/4 | {len(v['parent_successes_retained'])}/32 |")
    for arm, v in comparison["actual_finals"].items():
        tail = comparison["tail"][arm]
        lines += ["", f"## {arm}", "", "六条起身：" + "；".join(f"{r['motion']}：{'完整' if not r['failed'] else r['reason']}，{r['execution_seconds']:.2f}s" for r in v["getups"]),
            "", "父成功退化：" + (", ".join(v["parent_successes_lost"]) or "无"),
            "", "新增成功：" + (", ".join(v["newly_completed"]) or "无"),
            "", f"末三共同节点：{tail['available_common_iterations']}；回报均值/范围：{tail['mean_return_over_available_common_nodes']} / {tail['return_range_over_available_common_nodes']}。",
            "", f"三节点都成功的动作：{tail['three_node_success_intersection']}；其中起身：{tail['three_node_getup_intersection']}。",
            "", f"缺失预定节点：{tail['missing_predeclared_iterations']}。"]
    xy = comparison["xy_common_full_success"]
    lines += ["", "## 同集合 XY", "", f"共同完整成功集合共{xy['count']}条：" + ", ".join(xy["motion_names"]), ""]
    lines += [f"- {label}（{v['iteration']}）：平均XY误差 {v['subset_mean_xy_error_m']} m。" for label, v in xy["scores"].items()]
    lines += ["", "逐动作XY、所有节点评分和动作身份见 comparison.json；区间训练统计与原始产物路径见各arm目录。", "",
              "P4重点失败片段的观测与解释见 [旧轨迹分析](p4_trajectory_analysis.md)。", "",
              "这些是40条训练动作的单父版本、单seed结果，末三节点不是独立重复。半Actor学习率的比较不能证明唯一根因。", "", comparison["next_step"], "",
              "大权重、逐轮日志、原始评分轨迹和缓存保留服务器，待用户备份；备份未确认，不自动删除。"]
    (result / "conclusion.md").write_text("\n".join(lines) + "\n")


def finish(arm):
    protocol = read(PROTOCOL)
    spec = next(a for a in protocol["arms"] if a["id"] == arm)
    run = ROOT / "outputs/runs" / spec["run"]
    status = read(run / "status.json")
    final = status["iteration"]
    nodes = sorted(set(range(19000, final + 1, 1000)) | {final})
    publications = [publish(run.name, i, final=i == final) for i in nodes]
    with (ROOT / "work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        from analyze_p5_trajectories import final_failure_windows
        result = ROOT / "results" / protocol["campaign"]
        arm_dir = result / "arms" / arm
        summary = read(arm_dir / "summary.json")
        write(arm_dir / "failure_windows.json", final_failure_windows(run / f"evaluation_{final:07d}"))
        write(arm_dir / "training.json", training_summary(run))
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

        commit = push_results("p5-" + arm + "-completed", [result.relative_to(ROOT)], update)
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
                if line.startswith("> **当前入口：P5"):
                    lines[i] = f"> **当前入口：P5已完成训练、正式评分和关键结果发布。** {comparison['decision']} 见[最终分析](results/{protocol['campaign']}/conclusion.md)和[结果索引](results/{protocol['campaign']}/summary.json)。不自动追加训练。"
                    break
            readme.write_text("\n".join(lines) + "\n")
            plan = ROOT / "docs/P5_STABILITY_PLAN.md"
            lines = plan.read_text().splitlines()
            for i,line in enumerate(lines):
                if line.startswith("状态："):
                    lines[i] = f"状态：**训练、正式评分和关键结果已完成。** 见 [最终分析](../results/{protocol['campaign']}/conclusion.md)。"
                    break
            plan.write_text("\n".join(lines) + "\n")
            paths += [Path("README.md"), Path("docs/P5_STABILITY_PLAN.md")]
        push_results("p5-" + arm + "-publication-confirmed", paths, update)
        print("P5_ARM_COMPLETE", arm, final, campaign["status"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("arm", choices=("c0_control", "actor_half_lr"))
    finish(p.parse_args().arm)
