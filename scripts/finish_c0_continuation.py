"""Finish the one P4 C0 run using its existing full evaluations and trajectories."""
from pathlib import Path
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from publish_checkpoint import (
    ROOT, REPO, git, call, publish, ensure_release, release_by_tag,
    upload_files, push_results, archive_parts,
)
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


def selected_videos(parent, score):
    old={r["motion"]:r for r in parent["clips"]}
    names=[]
    for prefix in ("walk","run","dance","jumps","fallAndGetUp"):
        group=[r for r in score["clips"] if r["motion"].startswith(prefix)]
        gained=[r for r in group if old[r["motion"]]["failed"] and not r["failed"]]
        failed=[r for r in group if r["failed"]]
        chosen=gained[0] if gained else (min(failed,key=lambda r:r["completion_fraction"]) if failed else group[0])
        names.append(chosen["motion"])
    # Show remaining running/get-up failures and the previously earliest get-up.
    names += [r["motion"] for r in score["clips"] if r["failed"] and r["motion"].startswith(("run","fallAndGetUp"))]
    names.append("fallAndGetUp2_subject2")
    return list(dict.fromkeys(names))


def update_documents(tag, summary, comparison):
    final=comparison["final"]
    report=(f"P4 `{tag}`：第{final['iteration']}轮，{final['completed_motions']}/40完整执行，"
            f"完整时长归一化回报{final['mean_normalized_return']:.8f}；"
            f"起身{final['categories']['fallAndGetUp']['completed']}/6、跑步{final['categories']['run']['completed']}/4。"
            f"新增{summary['training_snapshot']['new_joint_updates']}次联合更新，"
            f"训练阶段{summary['training_snapshot']['stage_wall_seconds']/3600:.3f}小时（含一次64步预热）。"
            f"父版本29条成功保留{len(final['parent_successes_retained'])}条，新增完成{len(final['newly_completed'])}条，"
            f"退化{len(final['parent_successes_lost'])}条。训练、评估、发布和清理状态分别见"
            f"[结果](results/{tag}/summary.json)与[逐动作变化](results/{tag}/comparison.json)。"
            "该阶段不作为收敛证明，coverage不是论文成功率。")
    readme=ROOT/"README.md"
    text=readme.read_text()
    start=text.index("> **")
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
    text=text.replace("当前仅完成审阅与计划发布，训练需执行该启动提示词后开始。", "P4本段训练和正式评估已结束，实际发布/清理状态见本节末结果链接。")
    marker="\n<!-- P4_EXECUTION_RESULT -->\n"
    text=text.split(marker)[0]+marker+report.replace("](results/", "](../results/")+"\n\n"+summary["next_step_assessment"]+"\n"
    plan.write_text(text)
    prompt=ROOT/"docs/NEXT_STAGE_START_PROMPT.md"
    text=prompt.read_text()
    lines=text.splitlines()
    lines[2]=f"P4 `{tag}` 本段训练和评估已结束。下文保留原授权提示词；不要重复启动，实际发布/清理状态见 results/{tag}/summary.json。"
    prompt.write_text("\n".join(lines)+"\n")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("tag");tag=parser.parse_args().tag
    run=ROOT/"outputs/runs"/(tag+"-h32_aux_bce")
    result=ROOT/"results"/tag;result.mkdir(parents=True,exist_ok=True)
    stage=ROOT/"outputs/campaigns"/tag;stage.mkdir(exist_ok=True)
    status=json.loads((run/"status.json").read_text())
    started=(run/"status.json").stat().st_mtime
    runtime=json.loads((run/"runtime.json").read_text())
    protocol_path=ROOT/"configs/next_stage_continuation_protocol.json"
    protocol=json.loads(protocol_path.read_text())
    parent=json.loads((ROOT/protocol["parent"]["evaluation"]).read_text())
    final=status["iteration"]
    nodes=sorted(set(range((status["start_iteration"]//1000+1)*1000,final+1,1000))|{final})
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
    if not (stage/"videos/video_manifest.json").exists():
        with (stage/"render.log").open("a") as log:
            subprocess.run([sys.executable,"-u",str(ROOT/"scripts/render_goal_videos.py"),str(stage),str(final_dir),
                            "--labels","C0 aux BCE","--motions",*selected_videos(parent,score)],
                           stdout=log,stderr=subprocess.STDOUT,check=True)
    shutil.copy2(stage/"videos/video_manifest.json",result/"video_manifest.json")
    compact={k:v for k,v in score.items() if k not in ("clips","data_definition")}
    trend=[{"iteration":parent["iteration"],"completed_motions":parent["completed_motions"],"mean_normalized_return":parent["mean_normalized_return"]}]
    trend += [{k:s[k] for k in ("iteration","completed_motions","mean_normalized_return")} for s in evaluations.values()]
    increasing=len(trend)>=3 and trend[-1]["mean_normalized_return"]>trend[-2]["mean_normalized_return"]>trend[-3]["mean_normalized_return"]
    assessment=("最近三个正式节点回报持续提高，后续优先考虑接续同一路线；本次不自动增加预算。" if increasing else
                "最近三个正式节点未呈连续回报增长，需结合逐动作保持/退化与最终真实失败尾窗判断是否继续；本次不自动启动新分支。")
    summary={"tag":tag,"run":run.name,"status":"publishing","training_snapshot":status,
             "training_done":True,"full_clip_evaluation_done":score["status"]=="evaluated",
             "final_scores":compact,"final_iteration":final,"evaluated_iterations":nodes,
             "previous_elapsed_seconds":runtime["previous_elapsed_seconds"],
             "finalization_started_unix":started,"milestone_trend":trend,
             "next_step_assessment":assessment,
             "remaining_questions":["Long-motion survival and XY tracking remain separate; own-duration means are not a matched-prefix causal comparison.",
                                    "Auxiliary BCE is retained based on P3 control results; its mechanism and useful state Jacobians are not established.",
                                    "Training-motion coverage and this bounded stage do not establish generalization or convergence."],
             "cleanup":{"deleted":[],"released_bytes":0},"unpublished":[]}
    sp=result/"summary.json";write(sp,summary)
    release_tag="sm-"+tag+"-final"
    notes=stage/"release-notes.md"
    notes.write_text(f"P4 continuous C0 continuation: 9000 to {final}.\n\n"
        f"{score['completed_motions']}/40 complete; full-duration normalized return {score['mean_normalized_return']:.8f}. "
        f"{status['new_joint_updates']} new joint updates, {status['new_actor_updates']} new actor updates, "
        f"{status['stage_wall_seconds']:.1f} seconds including one 64-step replay warmup. "
        f"Previous elapsed {runtime['previous_elapsed_seconds']:.1f} seconds is separate.\n\n"
        "H32, k8, robot_root/710, aux_bce, analytic_smooth/0.05, state mean, optimizer and global LR schedule unchanged. "
        "Final scores and videos use the same actual trajectories. Parent evaluation is reused; no parent replay. "
        "Coverage is an additional diagnostic; this stage does not establish convergence.\n",encoding="utf-8")
    coverage={};assets=[];whitelist=[];pub_roots=[]
    milestone_missing=[]
    # Confirm already-uploaded names/sizes/URLs without downloading any history.
    for publication in publications:
        pub=ROOT/"outputs/publications"/publication["tag"];pub_roots.append(pub)
        remote={a["name"]:a for a in release_by_tag(publication["tag"])["assets"]}
        confirmed={a["name"]:a for a in publication["assets"]
                   if a["name"] in remote and remote[a["name"]]["state"]=="uploaded" and remote[a["name"]]["size"]==a["bytes"]}
        for asset in publication["assets"]:
            if asset["name"] in confirmed:
                coverage[asset["path"]]={"url":remote[asset["name"]]["browser_download_url"],"bytes":asset["bytes"]}
            else:
                milestone_missing.append({"path":asset["path"],"release":publication["tag"]})
        milestone_missing += publication["unpublished"]
        part_names=publication["trajectory_archive_parts"]
        if all(name in confirmed for name in part_names):
            links=[{"name":name,"url":remote[name]["browser_download_url"],"bytes":remote[name]["size"]} for name in part_names]
            archive=pub/"trajectories.tar"
            coverage[str(archive.relative_to(ROOT))]={"url":publication["release_url"],"bytes":archive.stat().st_size,"archive_parts":links}
            for raw in (run/f"evaluation_{publication['iteration']:07d}"/"trajectories").glob("*.npz"):
                coverage[str(raw.relative_to(ROOT))]={"url":publication["release_url"],"bytes":raw.stat().st_size,"member":"trajectories/"+raw.name,"archive_parts":links}
    for checkpoint in sorted(run.glob("checkpoint_*.pt")):
        if checkpoint.is_symlink():continue
        relative=str(checkpoint.relative_to(ROOT));whitelist.append(checkpoint)
        if relative not in coverage:
            target=stage/checkpoint.name
            if not target.exists():os.link(checkpoint,target)
            assets.append(target)
            coverage[relative]={"pending_assets":[target.name],"bytes":checkpoint.stat().st_size}
    parent_dir=ROOT/"outputs/parents"/tag
    inputs=json.loads((parent_dir/"inputs.json").read_text())
    for source in inputs["releases"]:
        remote={a["name"]:a for a in release_by_tag(source["tag"])["assets"]}
        asset=remote[source["name"]]
        if asset["state"]!="uploaded" or asset["size"]!=source["bytes"]:
            raise RuntimeError(f"Input asset is not confirmed uploaded: {source['name']}")
    coverage.update(inputs["files"])
    whitelist += [ROOT/path for path in inputs["files"]]
    roots=[run,stage,*pub_roots,parent_dir,ROOT/"data/processed/lafan1_g1_50hz"]
    logs=[ROOT/"outputs/campaigns"/(run.name+".train.log"),ROOT/"outputs/campaigns"/(tag+".restore.log")]
    logs += list((ROOT/"outputs/publications").glob(run.name+"-i*.log"))
    assets += [*sorted((stage/"videos").glob("*.mp4")),stage/"videos/contact_sheet.jpg"]
    archive=stage/"original_records.tar"
    archived=[]
    # Retain runtime/status/publication/input metadata as recovery records.
    preserved={"config.json","runtime.json","status.json","publication.json","inputs.json","archive-members.txt",".checkpoint.lock"}
    with tarfile.open(archive,"w") as tar:
        for root in [run,stage,*pub_roots]:
            for file in sorted(root.rglob("*")):
                if (not file.is_file() or file.is_symlink() or file==archive or file in assets
                    or file.name in preserved or file.name.startswith("original_records.tar.part")):continue
                relative=str(file.relative_to(ROOT));whitelist.append(file)
                if relative not in coverage:
                    tar.add(file,arcname=relative);archived.append(file)
        for file in logs:
            if file.exists():
                relative=str(file.relative_to(ROOT));tar.add(file,arcname=relative);whitelist.append(file);archived.append(file)
    parts=archive_parts(archive);assets+=parts;whitelist.append(archive)
    for file in [*archived,archive]:
        coverage[str(file.relative_to(ROOT))]={"pending_assets":[p.name for p in parts],"bytes":file.stat().st_size,
                                             "member":str(file.relative_to(ROOT)) if file!=archive else None}
    paths=[result.relative_to(ROOT),(ROOT/"results"/run.name).relative_to(ROOT),Path("README.md"),
           Path("docs/REPRODUCTION_PLAN.md"),Path("docs/NEXT_STAGE_START_PROMPT.md"),protocol_path.relative_to(ROOT)]
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        release=ensure_release(release_tag,"P4 continuous C0 / final",notes,git("rev-parse","HEAD"))
        uploaded,missing=upload_files(release_tag,assets,release["id"])
        by_name={a["name"]:a for a in uploaded}
        summary.update(release_url=f"https://github.com/{REPO}/releases/tag/{release_tag}",assets=uploaded,
                       unpublished=milestone_missing+missing)
        for record in coverage.values():
            pending=record.get("pending_assets")
            if pending and all(name in by_name for name in pending):
                record.update(url=summary["release_url"],archive_parts=[{"name":name,"url":by_name[name]["url"],"bytes":by_name[name]["bytes"]} for name in pending])
        for asset in uploaded:coverage[asset["path"]]={"url":asset["url"],"bytes":asset["bytes"]}
        summary["upload_inventory"]=coverage
        summary["status"]="uploaded" if not summary["unpublished"] else "upload_incomplete"
        update_documents(tag,summary,comparison)
        protocol.update(status=summary["status"],training_started=True)
        protocol["execution"].update({"campaign":tag,"run":run.name,
                        "final_iteration":final,"training_done":True,"full_clip_evaluation_done":True,
                        "summary":str(sp.relative_to(ROOT)),"release_url":summary["release_url"]})
        write(protocol_path,protocol);write(sp,summary)
        def update(index):
            index.setdefault("campaigns",{})[tag]={"status":summary["status"],"summary":str(sp.relative_to(ROOT)),"release_url":summary["release_url"]}
            index["next_stage"].update(status=summary["status"],campaign=tag,run=run.name,training_started=True,
                                      training_done=True,full_clip_evaluation_done=True,final_iteration=final,
                                      decision=assessment)
        summary["results_commit"]=push_results(release_tag,paths,update)
        # All training, evaluation, failure analysis, rendering and upload consumers ended.
        for file in dict.fromkeys(whitelist+assets):
            if not file.is_file() or file.is_symlink():continue
            relative=str(file.relative_to(ROOT));record=coverage.get(relative)
            if not record or not record.get("url") or file.stat().st_size!=record["bytes"]:continue
            if not any(file.resolve().is_relative_to(root.resolve()) for root in roots) and file not in logs:
                raise ValueError(f"Cleanup target outside exact P4 experiment paths: {file}")
            stat=file.stat()
            if stat.st_nlink==1:summary["cleanup"]["released_bytes"]+=stat.st_blocks*512
            file.unlink();summary["cleanup"]["deleted"].append({"path":relative,"bytes":stat.st_size})
        alias=run/"checkpoint_latest.pt"
        if alias.is_symlink() and not alias.exists():alias.unlink()
        summary["status"]="completed" if not summary["unpublished"] else "completed_with_unpublished_files"
        summary["finalization_wall_seconds"]=time.time()-started
        summary["completed_unix"]=time.time()
        protocol["status"]=summary["status"]
        protocol["execution"].update(deleted_files=len(summary["cleanup"]["deleted"]),
                                     released_bytes=summary["cleanup"]["released_bytes"],unpublished=summary["unpublished"])
        write(protocol_path,protocol);write(sp,summary)
        push_results(release_tag+"-cleanup",paths,update)
    print("P4_COMPLETE",json.dumps({k:summary[k] for k in ("status","final_iteration","release_url","unpublished")}),flush=True)


if __name__=="__main__":main()
