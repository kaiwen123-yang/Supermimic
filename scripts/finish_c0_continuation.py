"""Finish P4 with formal scores and lightweight Git results; retained artifacts belong to the user."""
from pathlib import Path
import argparse
import fcntl
import json
import time
from publish_checkpoint import ROOT, REPO, publish, push_results
from finish_tracking_campaign import training_summary, write
from finish_goal_campaign import get_up_failures


def compare_to_parent(parent, score):
    old={r["motion"]:r for r in parent["clips"]}
    rows=[{"motion":r["motion"],"parent":old[r["motion"]],"current":r,
           "delta_normalized_return":r["normalized_return"]-old[r["motion"]]["normalized_return"],
           "delta_execution_seconds":r["execution_seconds"]-old[r["motion"]]["execution_seconds"]}
          for r in score["clips"]]
    retained=[r["motion"] for r in rows if not r["parent"]["failed"] and not r["current"]["failed"]]
    lost=[r["motion"] for r in rows if not r["parent"]["failed"] and r["current"]["failed"]]
    gained=[r["motion"] for r in rows if r["parent"]["failed"] and not r["current"]["failed"]]
    categories={prefix:{"total":sum(r["motion"].startswith(prefix) for r in rows),
                        "completed":sum(r["motion"].startswith(prefix) and not r["current"]["failed"] for r in rows)}
                for prefix in ("run","fallAndGetUp")}
    return {"iteration":score["iteration"],"completed_motions":score["completed_motions"],
            "mean_normalized_return":score["mean_normalized_return"],
            "mean_completion_fraction":score["mean_completion_fraction"],
            "mean_tracking_coverage":score["mean_tracking_coverage"],
            "categories":categories,"parent_successes_retained":retained,
            "parent_successes_lost":lost,"newly_completed":gained,
            "original_eleven_failures":[r for r in rows if r["parent"]["failed"]],
            "running_and_getups":[r for r in rows if r["motion"].startswith(("run","fallAndGetUp"))],
            "clips":rows,
            "error_comparison_scope":"Each score reports its own executed trajectory. These are not matched-prefix XY/SO3/heading comparisons; parent trajectories were not restored or replayed."}


def update_documents(tag, summary, comparison):
    final=comparison["final"]
    report=(f"P4 `{tag}`：第{final['iteration']}轮，{final['completed_motions']}/40完整执行，"
            f"完整时长归一化回报{final['mean_normalized_return']:.8f}；"
            f"起身{final['categories']['fallAndGetUp']['completed']}/6、跑步{final['categories']['run']['completed']}/4。"
            f"新增{summary['training_snapshot']['new_joint_updates']}次联合更新，"
            f"训练阶段{summary['training_snapshot']['stage_wall_seconds']/3600:.3f}小时（含一次64步预热）。"
            f"父版本29条成功保留{len(final['parent_successes_retained'])}条，新增完成{len(final['newly_completed'])}条，"
            f"退化{len(final['parent_successes_lost'])}条。训练、评估、轻量发布及服务器产物位置见"
            f"[结果](results/{tag}/summary.json)与[逐动作变化](results/{tag}/comparison.json)。"
            "该阶段不作为收敛证明，coverage不是论文成功率。大产物留服务器待用户备份和删除，不阻塞本阶段完成。")
    readme=ROOT/"README.md"
    text=readme.read_text()
    start=text.index("> **P4")
    end=text.index("\n\n",start)
    text=text[:start]+"> **P4本段训练和正式评估已结束。** "+report+text[end:]
    text=text.replace("当前只完成审阅与计划发布，尚未启动P4。", "P4本段训练和正式评估已结束，实际状态与结果见本文顶部链接。")
    text=text.replace("P4已正式启动，当前训练进行中，实际进度见顶部运行记录。", "P4本段训练和正式评估已结束，实际状态与结果见本文顶部链接。")
    text=text.replace("下一步P4：一个C0连续run，9000→18000。", "P4：一个C0连续run，9000→实际最终节点。")
    readme.write_text(text)
    plan=ROOT/"docs/REPRODUCTION_PLAN.md"
    text=plan.read_text().replace("2026-11-03，计划已发布，尚未启动", "2026-11-03，已执行，实际结果见本节末")
    text=text.replace("2026-11-03，正式训练进行中", "2026-11-03，已执行，实际结果见本节末")
    text=text.replace("此次只审阅 GitHub 结果、原文和源码，发布下一步计划，没有启动训练、修改服务器环境或执行删除。",
                      "P4已获授权并执行，本节保留计划与证据，实际结果在本节末记录。")
    text=text.replace("当前仅完成审阅与计划发布，训练需执行该启动提示词后开始。", "P4本段训练和正式评估已结束，实际轻量发布和用户备份状态见本节末结果链接。")
    marker="\n<!-- P4_EXECUTION_RESULT -->\n"
    text=text.split(marker)[0]+marker+report.replace("](results/", "](../results/")+"\n\n"+summary["next_step_assessment"]+"\n"
    plan.write_text(text)
    prompt=ROOT/"docs/NEXT_STAGE_START_PROMPT.md"
    text=prompt.read_text()
    lines=text.splitlines()
    lines[2]=f"P4 `{tag}` 本段训练和评估已结束。下文保留原授权提示词；不要重复启动，实际轻量发布和用户备份状态见 results/{tag}/summary.json。"
    prompt.write_text("\n".join(lines)+"\n")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("tag");tag=parser.parse_args().tag
    run=ROOT/"outputs/runs"/(tag+"-h32_aux_bce")
    result=ROOT/"results"/tag;result.mkdir(parents=True,exist_ok=True)
    status=json.loads((run/"status.json").read_text())
    started=(run/"status.json").stat().st_mtime
    runtime=json.loads((run/"runtime.json").read_text())
    protocol_path=ROOT/"configs/next_stage_continuation_protocol.json"
    protocol=json.loads(protocol_path.read_text())
    parent=json.loads((ROOT/protocol["parent"]["evaluation"]).read_text())
    final=status["iteration"]
    nodes=sorted(set(range((status["start_iteration"]//1000+1)*1000,final+1,1000))|{final})
    # Each publish call uses the existing lock, reuses completed evaluations and pushes only lightweight data.
    publications=[publish(run.name,i,final=i==final) for i in nodes]
    evaluations={str(i):json.loads((run/f"evaluation_{i:07d}"/"evaluation.json").read_text()) for i in nodes}
    final_dir=run/f"evaluation_{final:07d}"
    score=evaluations[str(final)]
    comparison_path=result/"comparison.json"
    if comparison_path.exists():
        comparison=json.loads(comparison_path.read_text())
    else:
        comparison={"parent_iteration":status["start_iteration"],
                    "milestones":{i:compare_to_parent(parent,s) for i,s in evaluations.items()},
                    "final":compare_to_parent(parent,score),
                    "failure_windows":get_up_failures(run,final_dir,("run","fallAndGetUp"),final),
                    "failure_window_interpretation":"Only actual final failed running/get-up tails. Same-action predicted states enter analytic_smooth for predicted_failure_probability; this is not learned BCE head output. Contacts are reconstructed geometry, not measured forces."}
        write(comparison_path,comparison)
    training_path=result/"training.json"
    if not training_path.exists():
        training=training_summary(run)
        training["interpretation"]="One continuous C0 run; category sampling/failure/reset counts and global WM component errors come from existing training tensors. No category-specific WM errors are inferred."
        write(training_path,training)
    compact={k:v for k,v in score.items() if k not in ("clips","data_definition")}
    trend=[{"iteration":parent["iteration"],"completed_motions":parent["completed_motions"],"mean_normalized_return":parent["mean_normalized_return"]}]
    trend += [{k:s[k] for k in ("iteration","completed_motions","mean_normalized_return")} for s in evaluations.values()]
    increasing=len(trend)>=3 and trend[-1]["mean_normalized_return"]>trend[-2]["mean_normalized_return"]>trend[-3]["mean_normalized_return"]
    assessment=("最近三个正式节点回报持续提高，后续优先考虑接续同一路线；本次不自动增加预算。" if increasing else
                "最近三个正式节点未呈连续回报增长，需结合逐动作保持/退化与最终真实失败尾窗判断是否继续；本次不自动启动新分支。")
    summary={"tag":tag,"run":run.name,"status":"publishing","training_snapshot":status,
             "training_done":True,"full_clip_evaluation_done":score["status"]=="evaluated",
             "lightweight_results_published":False,
             "final_scores":compact,"final_iteration":final,"evaluated_iterations":nodes,
             "previous_elapsed_seconds":runtime["previous_elapsed_seconds"],
             "finalization_started_unix":started,"milestone_trend":trend,
             "next_step_assessment":assessment,
             "publication_policy":"lightweight_git_first_bulk_artifacts_local",
             "bulk_artifacts_status":"retained_on_server_by_policy",
             "server_artifacts":{"worktree":str(ROOT),"run_directory":str(run),
                 "final_checkpoint":str(run/f"checkpoint_{final:07d}.pt"),
                 "checkpoint_purpose":"complete network/optimizer/sampler/RNG for continuation",
                 "parent_checkpoint":str(ROOT/"outputs/parents"/tag/"checkpoint_0009000.pt"),
                 "trajectories":str(run/"evaluation_*/trajectories"),
                 "trajectory_purpose":"actual formal scoring and on-demand video; retain all milestones",
                 "processed_cache":str(ROOT/"data/processed/lafan1_g1_50hz"),
                 "input_copies":str(ROOT/"outputs/parents"/tag),
                 "logs":str(ROOT/"outputs/campaigns"/(run.name+".train.log")),
                 "existing_publication_files":str(ROOT/"outputs/publications"/("sm-"+run.name+"-i*")),
                 "still_in_use":[],"future_use":["final/milestone/parent checkpoint for continuation","processed cache for continuation/evaluation","scoring trajectories for analysis or on-demand rendering"],
                 "backup_status":"awaiting_user_export_not_confirmed","deletion_owner":"user"},
             "video_status":"on_demand_from_existing_scoring_trajectories",
             "remaining_questions":["Long-motion survival and XY tracking remain separate; own-duration means are not a matched-prefix causal comparison.",
                                    "Auxiliary BCE is retained based on P3 control results; its mechanism and useful state Jacobians are not established.",
                                    "Training-motion coverage and this bounded stage do not establish generalization or convergence."],
             "cleanup":{"policy":"user_managed_backup_and_stage_deletion","automatic_stage_cleanup":False,"deleted":[],"released_bytes":0},
             "unpublished":[],"finalization_wall_seconds":time.time()-started,"completed_unix":time.time(),
             "results_url":f"https://github.com/{REPO}/tree/main/results/{tag}"}
    sp=result/"summary.json"
    write(sp,summary)
    update_documents(tag,summary,comparison)
    protocol.update(status="publishing",training_started=True)
    protocol["execution"].update(final_iteration=final,training_done=True,full_clip_evaluation_done=True,
        lightweight_results_published=False,summary=str(sp.relative_to(ROOT)),results_url=summary["results_url"],
        bulk_artifacts_status=summary["bulk_artifacts_status"],backup_status="awaiting_user_export_not_confirmed",
        deleted_files=0,released_bytes=0,unpublished=[])
    write(protocol_path,protocol)
    paths=[result.relative_to(ROOT),(ROOT/"results"/run.name).relative_to(ROOT),Path("README.md"),
           Path("docs/REPRODUCTION_PLAN.md"),Path("docs/NEXT_STAGE_START_PROMPT.md"),protocol_path.relative_to(ROOT)]
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        def update(index):
            index.setdefault("campaigns",{})[tag]={"status":summary["status"],"summary":str(sp.relative_to(ROOT)),
                "results_url":summary["results_url"],"publication_policy":summary["publication_policy"],
                "server_run_directory":str(run),"bulk_artifacts_status":summary["bulk_artifacts_status"],
                "backup_status":"awaiting_user_export_not_confirmed"}
            index["next_stage"].update(status=summary["status"],campaign=tag,run=run.name,training_started=True,
                training_done=True,full_clip_evaluation_done=True,lightweight_results_published=summary["lightweight_results_published"],
                final_iteration=final,decision=assessment,publication_policy=summary["publication_policy"],
                bulk_artifacts_status=summary["bulk_artifacts_status"])
        commit=push_results("p4-"+tag+"-completed",paths,update)
        summary.update(status="completed",lightweight_results_published=True,results_commit=commit,
                       finalization_wall_seconds=time.time()-started,completed_unix=time.time())
        protocol["status"]="completed"
        protocol["execution"]["lightweight_results_published"]=True
        write(sp,summary);write(protocol_path,protocol)
        push_results("p4-"+tag+"-publication-confirmed",[sp.relative_to(ROOT),protocol_path.relative_to(ROOT)],update)
    print("P4_COMPLETE",json.dumps({"status":"completed","final_iteration":final,"results_commit":commit,
          "results_url":summary["results_url"],"bulk_artifacts_status":summary["bulk_artifacts_status"],"unpublished":[]}),flush=True)


if __name__=="__main__":main()
