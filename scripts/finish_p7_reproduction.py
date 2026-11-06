"""Finish each bounded P7 job with its own endpoints, cost and research question."""
import argparse
import fcntl
import statistics
import time
from pathlib import Path
from publish_checkpoint import publish, push_results
from finish_tracking_campaign import training_summary
from p7_results import ROOT, PROTOCOL, read, write, success, refresh_campaign, update_index


def update_documents(campaign):
    complete=campaign["status"]=="completed"
    status="已完成训练、正式评分、关键证据和轻量发布" if complete else "已启动，两路正式训练由独立tmux继续"
    handoff="本段已结束，不重复启动或自动开P8" if complete else "接续已有tmux，不重复启动、不重建replay或重置LR，不自动扩预算或开P8"
    paths=[Path("AGENTS.md"),Path("README.md"),Path("docs/P7_CONTINUATION_AND_FRESH_PLAN.md"),Path("docs/NEXT_STAGE_START_PROMPT.md")]
    for path in paths:
        lines=(ROOT/path).read_text().splitlines()
        if path.name=="AGENTS.md":
            for i,line in enumerate(lines):
                if line.startswith("- 当前入口为P7："):
                    lines[i]=f"- 当前入口为P7：docs/P7_CONTINUATION_AND_FRESH_PLAN.md、configs/next_stage_reproduction_protocol.json。P7{status}；状态见results/{campaign['campaign']}/summary.json。{handoff}；P1–P6为历史。"
                elif line.startswith("## P7实施"):
                    lines[i]=f"## P7实施（{status}）"
        elif path.name=="README.md":
            for i,line in enumerate(lines):
                if line.startswith("> **当前入口："):
                    lines[i]=f"> **当前入口：P7{status}。** continuation 33001–42000；from_scratch 1–9000。见[运行状态](results/{campaign['campaign']}/summary.json)与[P7计划](docs/P7_CONTINUATION_AND_FRESH_PLAN.md)。不重复启动或自动开P8。"
                    break
        elif path.name=="P7_CONTINUATION_AND_FRESH_PLAN.md":
            for i,line in enumerate(lines):
                if line.startswith("状态："):
                    lines[i]=f"状态：**{status}。** 实际任务状态见[结果索引](../results/{campaign['campaign']}/summary.json)。"
                    break
        else:
            lines[2]=f"P7{status}。先读results/{campaign['campaign']}/summary.json。下文保留授权范围；{handoff}。"
        (ROOT/path).write_text("\n".join(lines)+"\n")
    return paths


def finish(job_id):
    protocol=read(PROTOCOL)
    job=next(j for j in protocol["jobs"] if j["id"]==job_id)
    result=ROOT/"results"/protocol["campaign"]
    jobdir=result/"jobs"/job_id
    run=ROOT/"outputs/runs"/job["run"]
    status=read(run/"status.json")
    final=status["iteration"]
    nodes=sorted({i for i in job["evaluation_iterations"] if i<=final}|{final})
    publications=[publish(run.name,i,final=i==final) for i in nodes]
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        summary=read(jobdir/"summary.json")
        training=training_summary(run)
        write(jobdir/"training.json",training)
        views={str(i):read(ROOT/"results"/run.name/"milestones"/f"iteration_{i:07d}"/"comparison.json") for i in nodes}
        scores={i:read(run/f"evaluation_{i:07d}"/"evaluation.json") for i in nodes}
        final_score=scores[final]
        tail=[i for i in job["tail_iterations"] if i in scores]
        intersection=set.intersection(*(success(scores[i]) for i in tail)) if tail else set()
        comparison={"job":job_id,"initialization":job["initialization"],"question":job["question"],
            "fixed_endpoint":job["target_iteration"],"actual_endpoint":final,"fixed_endpoint_reached":final==job["target_iteration"],
            "all_milestones":views,"actual_final_node":str(final),
            "tail":{"prescribed_iterations":job["tail_iterations"],"available_iterations":tail,
                "missing_iterations":[i for i in job["tail_iterations"] if i not in scores],
                "mean_return":statistics.mean(scores[i]["mean_normalized_return"] for i in tail) if tail else None,
                "return_range":[min(scores[i]["mean_normalized_return"] for i in tail),max(scores[i]["mean_normalized_return"] for i in tail)] if tail else None,
                "available_success_intersection":sorted(intersection),
                "three_node_success_intersection":sorted(intersection) if tail==job["tail_iterations"] else None},
            "cost":{"new_training_iterations":final-job["start_iteration"],"wm_only_updates":training["wm_only_updates"],
                "actor_updates":training["actor_updates"],"new_sim_transitions":status["new_sim_transitions"],
                "cumulative_sim_transitions":status["sim_transitions"],"stage_wall_seconds":status["stage_wall_seconds"],
                "cumulative_wall_seconds":status["wall_seconds"],"previous_elapsed_seconds":read(run/"runtime.json")["previous_elapsed_seconds"],
                "runtime":str((run/"runtime.json")),"shared_gpu":True},
            "interpretation":"Different initialization histories; no cross-job A/B winner. Temporal nodes are not independent seeds."}
        if job["parent"] is not None:
            parent=read(ROOT/job["parent"]["evaluation"])
            names=sorted(success(parent)&success(final_score))
            matched={}
            for label,score in (("parent_B33000",parent),("continuation_final",final_score)):
                rows={r["motion"]:r for r in score["clips"]}
                matched[label]={key:{"mean":statistics.mean(rows[n][key] for n in names) if names else None,
                    "per_motion":{n:rows[n][key] for n in names}}
                    for key in ("mean_root_xy_error_m","mean_root_orientation_error_rad")}
            comparison["common_full_success"]={"motion_names":names,"count":len(names),"metrics":matched}
            comparison["tail"]["parent37_in_available_intersection"]=sorted(success(parent)&intersection)
            from p7_evidence import export_physical_window
            short=[]
            for row in final_score["clips"]:
                if row["failed"]:
                    end=row["executed_steps"]
                    short.append(export_physical_window(run,final,row["motion"],max(0,end-132),end,
                        jobdir/"final_failure_windows"))
            write(jobdir/"final_failure_windows"/"manifest.json",short)
        else:
            reached=[i for i in nodes if scores[i]["mean_normalized_return"]>=.82]
            first=reached[0] if reached else None
            comparison["first_observed_reference_crossing"]={"reference_return":.82,"iteration":first,
                "cost":read(ROOT/"results"/run.name/"milestones"/f"iteration_{first:07d}"/"training.json")["last"] if first else None,
                "subsequent_nodes":[{"iteration":i,"return":scores[i]["mean_normalized_return"],
                    "at_or_above_reference":scores[i]["mean_normalized_return"]>=.82} for i in nodes if first is not None and i>first],
                "meaning":"First observed saved full40 node, not the precise crossing time; no automatic extension if absent."}
        write(jobdir/"comparison.json",comparison)
        # Earlier failed Git pushes can be republished after the final node.
        # Bind completion metadata to the fixed actual endpoint, not retry order.
        final_view=views[str(final)]
        summary.update(latest_evaluated_iteration=final,
            latest_evaluation={key:final_score[key] for key in ("completed_motions","mean_normalized_return","mean_completion_fraction")},
            latest_reward_quality=final_view["reward_quality_mean"],
            latest_training_cost={key:training["last"][key] for key in ("stage_elapsed_seconds","elapsed_seconds",
                "new_actor_updates","new_sim_transitions","collected_sim_transitions")})
        summary["server_artifacts"].update(checkpoint=str(run/f"checkpoint_{final:07d}.pt"),
            trajectories=str(run/f"evaluation_{final:07d}"/"trajectories"))
        if job["parent"] is not None:
            summary.update(latest_parent_successes_retained=len(final_view["parent_successes_retained"]),
                latest_newly_completed=final_view["newly_completed"])
        summary.update(status="publishing",training_done=True,full_clip_evaluation_done=True,
            final_iteration=final,evaluated_iterations=nodes,training_snapshot=status,cost=comparison["cost"],
            final_scores={k:v for k,v in final_score.items() if k not in ("clips","data_definition")},
            evaluation_wall_seconds=sum(s["wall_seconds"] for s in scores.values()),
            publications=[{"iteration":p["iteration"],"results_commit":p["results_commit"],"url":p["result_url"]} for p in publications])
        write(jobdir/"summary.json",summary)
        lines=[f"# P7 {job_id} 结果","",job["question"],"",
            f"实际终点 {final}，约定终点 {job['target_iteration']}；完整成功 {final_score['completed_motions']}/40，回报 {final_score['mean_normalized_return']:.8f}，完成 {final_score['mean_completion_fraction']:.4%}。",
            f"本段 {comparison['cost']['new_training_iterations']} 次训练迭代，其中 WM-only {training['wm_only_updates']} 次、Actor/联合更新 {training['actor_updates']} 次；阶段 {status['stage_wall_seconds']/3600:.3f} 小时，累计 {status['wall_seconds']/3600:.3f} 小时。",
            f"预定尾三 {job['tail_iterations']}，实际可用 {tail}，均值 {comparison['tail']['mean_return']}；三节点成功交集见 comparison.json。","",
            "| 节点 | 完整成功 | 回报 | 完成比例 | 起身 | 跑步 |","|---|---:|---:|---:|---:|---:|"]
        for i in nodes:
            v=views[str(i)]
            lines.append(f"| {i} | {v['completed_motions']}/40 | {v['mean_normalized_return']:.8f} | {v['mean_completion_fraction']:.4%} | {v['categories']['fallAndGetUp']['completed']}/6 | {v['categories']['run']['completed']}/4 |")
        v=views[str(final)]
        if job["parent"] is not None:
            lines += ["",f"父37成功保留 {len(v['parent_successes_retained'])}/37；退化：{', '.join(v['parent_successes_lost']) or '无'}；新增完整：{', '.join(v['newly_completed']) or '无'}。",
                "共同完整集合XY/SO3、三条父失败身份、所有节点失败及奖励质量分解见 comparison.json。dance持续失败与曾成功后退化的起身/跳跃分别保留身份。"]
        else:
            lines += ["",f"首次观测达到0.82的已评分节点：{first if first is not None else '本段未观测到'}；对应从零成本与后续保持见 comparison.json。"]
        q=v["reward_quality_mean"]
        lines += ["",f"1−R={q['total_gap']:.8f}=(1−C) {q['missing_tail_gap']:.8f}+(C−R) {q['executed_quality_gap']:.8f}。逐动作8项积分在各节点 evaluation.json 中。",
            "", "固定终点与全部节点如实报告；两任务起点历史不同，不比较算法胜负。本段结束，不自动扩预算或开P8。",
            "",f"大权重、完整评分轨迹与逐轮日志保留于 {run}；备份未确认，删除由用户管理。"]
        (jobdir/"conclusion.md").write_text("\n".join(lines)+"\n")
        campaign=refresh_campaign(protocol)
        commit=push_results("p7-"+job_id+"-completed",[result.relative_to(ROOT)],lambda index:update_index(index,campaign))
        summary.update(status="completed",lightweight_results_published=True,results_commit=commit,completed_unix=time.time())
        write(jobdir/"summary.json",summary)
        campaign=refresh_campaign(protocol)
        protocol.update(status=campaign["status"])
        protocol["execution"].update(status=campaign["status"],training_done=campaign["training_done"],
            formal_evaluation_done=campaign["full_clip_evaluation_done"],key_results_published=campaign["lightweight_results_published"],
            evidence_backfill_done=campaign["evidence_backfill"]["status"]=="published",
            jobs={name:j["status"] for name,j in campaign["jobs"].items()})
        write(PROTOCOL,protocol)
        if campaign["status"]=="completed":
            (result/"conclusion.md").write_text("# P7 两个研究任务已完成\n\n"+
                "\n\n".join(f"## {name}\n\n"+(result/"jobs"/name/"conclusion.md").read_text().split("\n",1)[1] for name in campaign["jobs"])+"\n")
        paths=[result.relative_to(ROOT),PROTOCOL.relative_to(ROOT),*update_documents(campaign)]
        push_results("p7-"+job_id+"-publication-confirmed",paths,lambda index:update_index(index,campaign))
        print("P7_JOB_COMPLETE",job_id,final,campaign["status"],flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("job",choices=("continuation","from_scratch"))
    finish(parser.parse_args().job)
