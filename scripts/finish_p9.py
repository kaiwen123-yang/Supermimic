"""Stop at the actual bounded endpoint, score once, publish all prescribed nodes."""
import argparse
import fcntl
import statistics
import subprocess
import sys
import time
from pathlib import Path
from p9_results import ROOT, PROTOCOL, read, write, success, refresh, index_update, compare_lafan
from publish_p9 import publish
from publish_checkpoint import push_results
from finish_tracking_campaign import training_summary


def finish(job_id):
    protocol = read(PROTOCOL)
    job = protocol["jobs"][job_id]
    run = ROOT / "outputs/runs" / job["run"]
    result = ROOT / "results" / protocol["campaign"]
    jobdir = result / "jobs" / job_id
    status = read(run / "status.json")
    final = status["iteration"]
    nodes = sorted({i for i in job["evaluation_iterations"] if i <= final} | {final})
    publications = [publish(run.name, i, i == final) for i in nodes]
    with Path(protocol["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        scores = {i: read(run / f"evaluation_{i:07d}/evaluation.json") for i in nodes}
        views = {str(i): read(ROOT / "results" / run.name / "milestones" / f"iteration_{i:07d}/comparison.json") for i in nodes}
        score = scores[final]
        training = training_summary(run)
        write(jobdir / "training.json", training)
        tail = [i for i in job.get("tail_iterations", []) if i in scores]
        runtime = read(run / "runtime.json")
        comparison = {"actual_endpoint": final, "target_endpoint": job["target_iteration"], "all_milestones": views,
            "tail": {"prescribed_iterations": job.get("tail_iterations", []), "available_iterations": tail,
                "mean_return": statistics.mean(scores[i]["mean_normalized_return"] for i in tail) if tail else None,
                "available_success_intersection": sorted(set.intersection(*(success(scores[i]) for i in tail))) if tail else [],
                "complete_tail_available": tail == job.get("tail_iterations", [])},
            "cost": {"stage_wall_seconds": status["stage_wall_seconds"], "cumulative_wall_seconds": status["wall_seconds"],
                "inherited_training_seconds": protocol["source"]["total_known_training_seconds"],
                "total_known_training_seconds": protocol["source"]["total_known_training_seconds"] + status["stage_wall_seconds"],
                "new_training_iterations": status["new_training_iterations"], "new_actor_updates": status["new_actor_updates"],
                "new_sim_transitions": status["new_sim_transitions"],
                "imagination_steps": status["new_actor_updates"] * 4096 * protocol["common_training"]["imagination_horizon"], "shared_gpu": True}}
        if job_id.startswith("lafan"):
            from p7_evidence import export_physical_window
            windows = [export_physical_window(run, final, row["motion"], max(0, row["executed_steps"] - 132),
                row["executed_steps"], jobdir / "final_failure_windows") for row in score["clips"] if row["failed"]]
            write(jobdir / "final_failure_windows/manifest.json", windows)
        else:
            import shutil
            tails = run / f"evaluation_{final:07d}/failure_tails"
            shutil.copytree(tails, jobdir / "final_failure_windows", dirs_exist_ok=True)
            retention = run / f"lafan_retention_{final:07d}"
            if not (retention / "evaluation.json").exists():
                subprocess.run([sys.executable, "-u", str(ROOT / "scripts/evaluate.py"),
                    str(run / f"checkpoint_{final:07d}.pt"), "--output-dir", str(retention),
                    "--cross-dataset", "data/processed/lafan1_g1_50hz"], check=True, cwd=ROOT)
            shutil.copy2(retention / "evaluation.json", jobdir / "lafan_retention.json")
            comparison["interpretation"] = "H32-51000 weights transfer with inherited cost retained; not from scratch or a three-hour reproduction."
        write(jobdir / "comparison.json", comparison)
        summary = read(jobdir / "summary.json")
        summary.update(status="publishing", training_done=True, full_clip_evaluation_done=True,
            final_iteration=final, training_snapshot=status, cost=comparison["cost"],
            evaluated_iterations=nodes, publications=publications,
            evaluation_wall_seconds=sum(s["wall_seconds"] for s in scores.values()))
        write(jobdir / "summary.json", summary)
        lines = [f"# P9 {job_id} 实际结果", "",
            f"实际终点 {final}，目标 {job['target_iteration']}。完整成功 {score['completed_motions']}/{score['motions']}，全动作回报 {score['mean_normalized_return']:.8f}，完成比例 {score['mean_completion_fraction']:.4%}。",
            f"本阶段 {status['new_training_iterations']} 次训练迭代、{status['new_actor_updates']} 次Actor更新，累计本阶段 {status['stage_wall_seconds']/3700:.4f}h；H32-51000前序训练 {protocol['source']['total_known_training_seconds']/3700:.4f}h 单列。", "",
            "| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |", "|---|---:|---:|---:|---:|"]
        for i in nodes:
            v = views[str(i)]
            lines.append(f"| {i} | {v['completed_motions']}/{scores[i]['motions']} | {v['mean_normalized_return']:.8f} | {v['mean_completion_fraction']:.4%} | {len(v.get('parent_successes_retained', []))}/{v.get('parent_success_denominator', 0)} |")
        lines += ["", f"尾节点：{comparison['tail']}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。",
            "", "这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P10。",
            "", f"大产物保留在 {run}；用户备份未确认，不自动清理。"]
        if not job_id.startswith("lafan"):
            lines += ["", comparison["interpretation"]]
        (jobdir / "conclusion.md").write_text("\n".join(lines) + "\n")
        compare_lafan(protocol)
        campaign = refresh()
        commit = push_results(f"p9-{job_id}-completed", [result.relative_to(ROOT), (ROOT / "results" / run.name).relative_to(ROOT)], lambda index: index_update(index, campaign))
        summary.update(status="completed", lightweight_results_published=True, results_commit=commit, completed_unix=time.time())
        write(jobdir / "summary.json", summary)
        compare_lafan(protocol)
        campaign = refresh()
        protocol["status"] = campaign["status"]
        write(PROTOCOL, protocol)
        push_results(f"p9-{job_id}-publication-confirmed", [result.relative_to(ROOT), PROTOCOL.relative_to(ROOT)], lambda index: index_update(index, campaign))
        print("P9_JOB_COMPLETE", job_id, final, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    finish(parser.parse_args().job)
