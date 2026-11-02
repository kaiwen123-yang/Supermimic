"""Close the bounded P3 H32 pair using actual trajectories and confirmed uploads."""
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
import numpy as np
from publish_checkpoint import ROOT, REPO, git, call, publish, ensure_release, upload_files, push_results, archive_parts
from finish_goal_campaign import compare, get_up_failures

ARMS=("h32_aux_bce", "h32_state_only")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n")


def training_summary(run):
    rows=[json.loads(line) for line in (run/"metrics.jsonl").read_text().splitlines()]
    groups={}
    for stop in sorted({((r["iteration"]-1)//1000+1)*1000 for r in rows}):
        block=[r for r in rows if stop-1000<r["iteration"]<=stop]
        means={key:float(np.mean([r[key] for r in block])) for key in (
            "wm_normalized_state_mse","sim_step_reward","sim_step_termination_fraction",
            "imagined_discounted_return","collection_seconds","world_seconds","policy_critic_seconds","checkpoint_write_seconds")}
        means["wm_termination_bce"]=float(np.mean([r["wm_termination_bce"] for r in block])) if block[0]["wm_termination_bce"] is not None else None
        means["wm_state_components"]={k:float(np.mean([r["wm_state_components"][k] for r in block])) for k in block[0]["wm_state_components"]}
        families={k:{field:sum(r[field][k] for r in block) for field in ("family_transitions","family_failure_count","family_reset_samples")} for k in block[0]["family_transitions"]}
        total=sum(v["family_transitions"] for v in families.values())
        resets=sum(v["family_reset_samples"] for v in families.values())
        for value in families.values():
            value["transition_share"]=value["family_transitions"]/total
            value["reset_sample_share"]=value["family_reset_samples"]/resets if resets else None
        groups[str(stop)]={"first_iteration":block[0]["iteration"],"last_iteration":block[-1]["iteration"],"updates":len(block),"means":means,"families":families}
    return {"updates":len(rows),"first":rows[0],"last":rows[-1],"blocks":groups,
            "interpretation":"Training WM errors use each arm's own evolving replay; cross-model same-action errors on identical real failure windows are recorded separately."}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("tag");tag=parser.parse_args().tag
    result=ROOT/"results"/tag;result.mkdir(parents=True,exist_ok=True)
    stage=ROOT/"outputs/campaigns"/tag;stage.mkdir(exist_ok=True)
    runs={arm:ROOT/"outputs/runs"/(tag+"-"+arm) for arm in ARMS}
    statuses={arm:json.loads((run/"status.json").read_text()) for arm,run in runs.items()}
    # Reuse completed evaluations/uploads. Only unfinished publications are retried.
    for arm,run in runs.items():
        final=statuses[arm]["iteration"]
        for iteration in sorted(set(range(7000,final+1,1000))|{final}):
            publish(run.name,iteration,final=iteration==final)
    finals={arm:run/f"evaluation_{statuses[arm]['iteration']:07d}" for arm,run in runs.items()}
    common=set.intersection(*[{int(p.name.split('_')[-1]) for p in run.glob('evaluation_*') if (p/'evaluation.json').exists()} for run in runs.values()])
    comparisons={str(i):compare(runs[ARMS[0]]/f"evaluation_{i:07d}",runs[ARMS[1]]/f"evaluation_{i:07d}") for i in sorted(common)}
    failure_windows={}
    for source,ev in finals.items():
        failure_windows[source]={model:get_up_failures(run,ev,("run","fallAndGetUp"),statuses[model]["iteration"]) for model,run in runs.items()}
    comparison={"A":"C0 h32_aux_bce","B":"C1 h32_state_only","common_iterations":sorted(common),
                "milestones":comparisons,"final":compare(finals[ARMS[0]],finals[ARMS[1]]),
                "failure_windows_by_source_then_model":failure_windows,
                "failure_window_interpretation":"Each source is an actual failed running/get-up trajectory. Both final world models receive that same recorded state, context and action sequence for same-action prediction; closed-loop predictions use their respective actors."}
    write(result/"comparison.json",comparison)
    training={arm:training_summary(run) for arm,run in runs.items()}
    write(result/"training.json",training)
    if not (stage/"videos/video_manifest.json").exists():
        with (stage/"render.log").open("a") as log:
            subprocess.run([sys.executable,"-u",str(ROOT/"scripts/render_goal_videos.py"),str(stage),str(finals[ARMS[0]]),str(finals[ARMS[1]]),"--labels","C0 aux BCE","C1 state only"],stdout=log,stderr=subprocess.STDOUT,check=True)
    shutil.copy2(stage/"videos/video_manifest.json",result/"video_manifest.json")
    scores={arm:json.loads((ev/"evaluation.json").read_text()) for arm,ev in finals.items()}
    selected={arm:[r for r in score["clips"] if r["motion"].startswith(("run","fallAndGetUp"))] for arm,score in scores.items()}
    compact_scores={arm:{k:v for k,v in score.items() if k not in ("clips","data_definition")} for arm,score in scores.items()}
    summary={"tag":tag,"status":"publishing","runs":statuses,"final_scores":compact_scores,
             "common_iterations":sorted(common),"running_and_getup_clips":selected,
             "interpretation":"Bounded 3000-update continuation, not convergence. Auxiliary BCE may help or harm. Interpret complete-duration returns, termination and matched actual failure-window prediction together; coverage is not paper success rate.",
             "cleanup":{"deleted":[],"released_bytes":0},"unpublished":[]}
    sp=result/"summary.json";write(sp,summary)
    release_tag="sm-"+tag+"-final"
    notes=stage/"release-notes.md"
    notes.write_text("P3 v2 H32 continuation from the same B6000 network/optimizer/sampler/RNG state.\n\n"+"\n".join(
        f"{arm}: global iteration {score['iteration']}, {score['completed_motions']}/40 complete, full-duration normalized return {score['mean_normalized_return']:.8f}; {statuses[arm]['new_joint_updates']} new joint updates in {statuses[arm]['stage_wall_seconds']:.1f} s."
        for arm,score in scores.items())+"\n\nOnly world termination BCE differs. State mean reduction, H32, analytic_smooth, robot_root and global LR schedule are unchanged. Videos use final scoring trajectories; no second physical replay. Training length does not establish convergence.\n",encoding="utf-8")
    coverage={};assets=[];whitelist=[]
    publications=[]
    for arm,run in runs.items():
        for pub in sorted((ROOT/"outputs/publications").glob("sm-"+run.name+"-i*")):
            if not pub.is_dir():continue
            publications.append(pub)
            status=json.loads((pub/"publication.json").read_text())
            for asset in status.get("assets",[]):
                coverage[asset["path"]]={"url":asset["url"],"bytes":asset["bytes"]}
            names=status.get("trajectory_archive_parts",["trajectories.tar"])
            parts=[a for a in status.get("assets",[]) if a["name"] in names]
            if len(parts)==len(names):
                links=[{"name":a["name"],"url":a["url"],"bytes":a["bytes"]} for a in parts]
                archive=pub/"trajectories.tar"
                coverage[str(archive.relative_to(ROOT))]={"url":status["release_url"],"bytes":archive.stat().st_size,"archive_parts":links}
                for raw in (run/f"evaluation_{status['iteration']:07d}"/"trajectories").glob("*.npz"):
                    coverage[str(raw.relative_to(ROOT))]={"url":status["release_url"],"bytes":raw.stat().st_size,"member":"trajectories/"+raw.name,"archive_parts":links}
        for cp in sorted(run.glob("checkpoint_*.pt")):
            if cp.is_symlink():continue
            relative=str(cp.relative_to(ROOT));whitelist.append(cp)
            if relative not in coverage:
                target=stage/(arm+"-"+cp.name)
                if not target.exists():os.link(cp,target)
                assets.append(target)
                coverage[relative]={"pending_assets":[target.name],"bytes":cp.stat().st_size}
    # The parent and fixed working data already have published assets. Reuse them.
    parent=ROOT/"outputs/parents"/tag
    inputs=json.loads((parent/"inputs.json").read_text())
    coverage.update(inputs["files"])
    roots=[*runs.values(),stage,*publications,parent,ROOT/"data/raw/lafan1_g1",ROOT/"data/processed/lafan1_g1_50hz"]
    logs=[ROOT/"outputs/campaigns"/(run.name+".train.log") for run in runs.values()]
    logs += [p for run in runs.values() for p in (ROOT/"outputs/publications").glob(run.name+"-i*.log")]
    assets += [*sorted((stage/"videos").glob("*.mp4")),stage/"videos/contact_sheet.jpg"]
    archive=stage/"original_records.tar"
    archived=[]
    with tarfile.open(archive,"w") as tar:
        for root in roots:
            for file in sorted(root.rglob("*")):
                if not file.is_file() or file.is_symlink() or file==archive or file in assets or file.name.startswith("original_records.tar.part"):continue
                relative=str(file.relative_to(ROOT));whitelist.append(file)
                if relative not in coverage:
                    tar.add(file,arcname=relative);archived.append(file)
        for file in logs:
            if file.exists():
                relative=str(file.relative_to(ROOT));tar.add(file,arcname=relative);whitelist.append(file);archived.append(file)
    parts=archive_parts(archive);assets+=parts;whitelist.append(archive)
    for file in [*archived,archive]:
        coverage[str(file.relative_to(ROOT))]={"pending_assets":[p.name for p in parts],"bytes":file.stat().st_size,"member":str(file.relative_to(ROOT)) if file!=archive else None}
    paths=[result.relative_to(ROOT),Path("README.md"),Path("docs/REPRODUCTION_PLAN.md")]
    paths += [(ROOT/"results"/run.name).relative_to(ROOT) for run in runs.values()]
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        release=ensure_release(release_tag,"P3 H32 auxiliary BCE / complete pair",notes,git("rev-parse","HEAD"))
        uploaded,missing=upload_files(release_tag,assets,release["id"])
        by_name={a["name"]:a for a in uploaded}
        summary.update(release_url=f"https://github.com/{REPO}/releases/tag/{release_tag}",assets=uploaded,unpublished=missing)
        for record in coverage.values():
            pending=record.get("pending_assets")
            if pending and all(name in by_name for name in pending):
                record.update(url=summary["release_url"],archive_parts=[{"name":name,"url":by_name[name]["url"],"bytes":by_name[name]["bytes"]} for name in pending])
        for asset in uploaded:coverage[asset["path"]]={"url":asset["url"],"bytes":asset["bytes"]}
        summary["upload_inventory"]=coverage
        summary["status"]="uploaded" if not missing else "upload_incomplete"
        write(sp,summary)
        def update(index):
            index.setdefault("campaigns",{})[tag]={"status":summary["status"],"summary":str(sp.relative_to(ROOT)),"release_url":summary["release_url"]}
            index["next_stage"].update(status=summary["status"],campaign=tag,training_started=True)
        report="\nP3 v2 实际阶段结果："+"；".join(f"{arm} 第{s['iteration']}轮，{s['completed_motions']}/40，归一化回报{s['mean_normalized_return']:.8f}，新增{statuses[arm]['new_joint_updates']}轮/{statuses[arm]['stage_wall_seconds']/3600:.3f}h" for arm,s in scores.items())+f"。结果和实际失败窗口见 results/{tag}/summary.json、comparison.json；该阶段不能作为充分收敛证据。\n"
        for document in (ROOT/"README.md",ROOT/"docs/REPRODUCTION_PLAN.md"):
            with document.open("a") as stream:stream.write(report)
        summary["results_commit"]=push_results(release_tag,paths,update)
        call(["gh","release","edit",release_tag,"--repo",REPO,"--draft=false","--latest=false","--notes-file",str(notes)])
        # Training, evaluation, rendering and upload consumers have all exited.
        for file in dict.fromkeys(whitelist+assets):
            if not file.is_file() or file.is_symlink():continue
            relative=str(file.relative_to(ROOT));record=coverage.get(relative)
            if not record or not record.get("url") or file.stat().st_size!=record["bytes"]:continue
            if not any(file.resolve().is_relative_to(root.resolve()) for root in roots) and file not in logs:
                raise ValueError(f"Cleanup target outside explicit P3 paths: {file}")
            stat=file.stat()
            if stat.st_nlink==1:summary["cleanup"]["released_bytes"]+=stat.st_blocks*512
            file.unlink();summary["cleanup"]["deleted"].append({"path":relative,"bytes":stat.st_size})
        for run in runs.values():
            alias=run/"checkpoint_latest.pt"
            if alias.is_symlink() and not alias.exists():alias.unlink()
        summary["status"]="completed" if not missing else "completed_with_unpublished_files"
        write(sp,summary)
        push_results(release_tag+"-cleanup",paths,update)
    print("P3_COMPLETE",json.dumps({k:summary[k] for k in ("status","release_url","unpublished")}),flush=True)


if __name__=="__main__":main()
