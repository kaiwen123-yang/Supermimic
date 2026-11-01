"""Complete the P2 pair: comparison, videos, retained assets, then exact-file cleanup."""
from pathlib import Path
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import numpy as np
from publish_checkpoint import ROOT, REPO, call, git, ensure_release, upload_files, push_results


def compare(a,b):
    ea=json.loads((a/"evaluation.json").read_text()); eb=json.loads((b/"evaluation.json").read_text())
    rows=[]
    for ra,rb in zip(ea["clips"],eb["clips"]):
        name=ra["motion"]
        aa=np.load(a/"trajectories"/(name+".npz")); bb=np.load(b/"trajectories"/(name+".npz"))
        n=min(ra["executed_steps"]-int(ra["failed"]),rb["executed_steps"]-int(rb["failed"]))
        row={"motion":name,"common_surviving_steps":n,"common_surviving_seconds":n*.02,
             "A":ra,"B":rb,"delta_B_minus_A_return":rb["normalized_return"]-ra["normalized_return"]}
        row["common_prefix"]={}
        for key in ("root_position_error_m","root_xy_error_m","root_orientation_error_rad","joint_rmse_rad","relative_body_position_error_m"):
            row["common_prefix"][key]={"A":float(aa[key][:n].mean()) if n else None,"B":float(bb[key][:n].mean()) if n else None}
        upright=aa["upright"][:n]&bb["upright"][:n]
        row["common_prefix"]["heading_error_upright_rad"]={"steps":int(upright.sum()),
            "A":float(aa["heading_error_rad"][:n][upright].mean()) if upright.any() else None,
            "B":float(bb["heading_error_rad"][:n][upright].mean()) if upright.any() else None}
        rows.append(row)
    categories={}
    for category in sorted({re.match(r"[A-Za-z]+", r["motion"])[0] for r in rows}):
        selected=[r for r in rows if re.match(r"[A-Za-z]+", r["motion"])[0]==category]
        if selected:
            categories[category]={"count":len(selected),**{arm:{"completed":sum(not r[arm]["failed"] for r in selected),
                "mean_normalized_return":float(np.mean([r[arm]["normalized_return"] for r in selected])),
                "mean_tracking_coverage":float(np.mean([r[arm]["tracking_coverage"] for r in selected]))} for arm in ("A","B")}}
    aggregate={key:{arm:float(np.mean([r["common_prefix"][key][arm] for r in rows if r["common_prefix"][key][arm] is not None]))
                   for arm in ("A","B")} for key in ("root_position_error_m","root_xy_error_m","root_orientation_error_rad","heading_error_upright_rad")}
    return {"A_iteration":ea["iteration"],"B_iteration":eb["iteration"],"common_prefix_motion_mean":aggregate,
            "categories":categories,"clips":rows,
            "A":{k:v for k,v in ea.items() if k not in ("clips","data_definition","protocol")},
            "B":{k:v for k,v in eb.items() if k not in ("clips","data_definition","protocol")}}


def get_up_failures(run,evaluation):
    """Only actual failed get-ups: contact and same-action prediction near failure."""
    sys.path.insert(0,str(ROOT))
    import mujoco
    import torch
    from supermimic.robot import load_model
    from supermimic.networks import WorldModel,Actor
    from supermimic.geometry import quat_mul,quat_inv,quat_to_rotvec
    from supermimic.motion import MotionLibrary
    from supermimic.task import observation
    from supermimic.robot import joint_arrays
    ev=json.loads((evaluation/"evaluation.json").read_text())
    failures=[r for r in ev["clips"] if r["failed"] and r["motion"].startswith("fallAndGetUp")]
    if not failures:return []
    torch.set_num_threads(2)
    checkpoint=torch.load(run/f"checkpoint_{ev['iteration']:07d}.pt",map_location="cpu",weights_only=False)
    world=WorldModel().cuda().eval();world.load_state_dict(checkpoint["world_model"])
    actor=Actor().cuda().eval();actor.load_state_dict(checkpoint["actor"])
    del checkpoint
    motions=MotionLibrary(ROOT/"data/processed/lafan1_g1_50hz","cuda")
    model=load_model();data=mujoco.MjData(model)
    context=torch.zeros((1,33),device="cuda");context[:,0]=1
    q0=torch.tensor(joint_arrays()["q0"],dtype=torch.float32,device="cuda")
    reports=[]
    with torch.no_grad():
        for row in failures:
            z=np.load(evaluation/"trajectories"/(row["motion"]+".npz"))
            end=row["executed_steps"];start=max(0,end-32)
            initial=np.concatenate((z["qpos"][start],z["qvel"][start],z["previous_action"][start]))
            predicted=torch.tensor(initial[None],device="cuda");closed=predicted.clone()
            states=[]
            for t in range(max(0,start-9),start+1):
                previous=z["previous_action"][t] if t<end else z["action"][-1]
                states.append(observation(torch.tensor(z["qpos"][t:t+1],device="cuda"),torch.tensor(z["qvel"][t:t+1],device="cuda"),
                    torch.tensor(previous[None],device="cuda"),q0,context[:,1:30]))
            while len(states)<10:states.insert(0,states[0])
            history=torch.stack(states,dim=1)
            cid=torch.tensor([motions.names.index(row["motion"])],device="cuda")
            horizons=[]
            for t in range(start,end):
                action=torch.tensor(z["action"][t:t+1],device="cuda")
                predicted=world(predicted,action,context)
                goal=motions.goal(cid,torch.tensor([t],device="cuda"),goal_frame=ev["goal_frame"],root_quaternion=closed[:,3:7])
                closed_action=actor(history,goal)
                closed=world(closed,closed_action,context)
                history=torch.cat((history[:,1:],observation(closed[:,:36],closed[:,36:71],closed[:,71:],q0,context[:,1:30])[:,None]),1)
                actual=torch.tensor(z["qpos"][t+1:t+2],device="cuda")
                if t-start+1 in (1,8,16,32) or t==end-1:
                    ref=motions.get(cid,torch.tensor([t+1],device="cuda"))["qpos"]
                    horizons.append({"steps":t-start+1,"same_action_root_position_error_m":float((predicted[:,:3]-actual[:,:3]).norm()),
                        "same_action_root_orientation_error_rad":float(quat_to_rotvec(quat_mul(predicted[:,3:7],quat_inv(actual[:,3:7]))).norm()),
                        "closed_loop_root_position_error_m":float((closed[:,:3]-actual[:,:3]).norm()),
                        "predicted_failure_probability":float(world.termination_probability(predicted,ref,"analytic_smooth",.05)[0])})
            contacts=[]
            for t in (start,end):
                data.qpos[:]=z["qpos"][t];data.qvel[:]=z["qvel"][t];mujoco.mj_forward(model,data)
                contacts.append({"time_seconds":t*.02,"contacts":[{"geom1":model.geom(c.geom1).name,"geom2":model.geom(c.geom2).name,
                    "distance_m":float(c.dist)} for c in data.contact[:data.ncon]]})
            reports.append({"motion":row["motion"],"failure_seconds":row["failure_seconds"],"reason":row["reason"],
                "failure_height_error_m":float(z["root_height_error_m"][-1]),"failure_tilt_error":float(z["tilt_error"][-1]),
                "window_start_seconds":start*.02,"prediction":horizons,"contacts":contacts})
    return reports


def main():
    p=argparse.ArgumentParser();p.add_argument("tag");a=p.parse_args();tag=a.tag
    result=ROOT/"results"/tag;result.mkdir(parents=True,exist_ok=True)
    stage=ROOT/"outputs/campaigns"/tag;stage.mkdir(exist_ok=True)
    runs={mode:ROOT/"outputs/runs"/(tag+"-"+mode) for mode in ("reference_heading","robot_root")}
    statuses={mode:json.loads((run/"status.json").read_text()) for mode,run in runs.items()}
    finals={mode:run/f"evaluation_{statuses[mode]['iteration']:07d}" for mode,run in runs.items()}
    # Failed uploads never trigger another simulation; missing final evaluations still run once.
    for mode,ev in finals.items():
        if not (ev/"evaluation.json").exists():
            subprocess.run([sys.executable,"-u",str(ROOT/"scripts/evaluate.py"),str(runs[mode]/f"checkpoint_{statuses[mode]['iteration']:07d}.pt")],check=True)
    common=set.intersection(*[{int(p.name.split('_')[-1]) for p in run.glob('evaluation_*') if (p/'evaluation.json').exists()} for run in runs.values()])
    common_iteration=max(common) if common else None
    comparison=compare(finals["reference_heading"],finals["robot_root"])
    comparison["largest_common_evaluated_iteration"]=common_iteration
    comparison["same_iteration_comparison"]=compare(runs["reference_heading"]/f"evaluation_{common_iteration:07d}",runs["robot_root"]/f"evaluation_{common_iteration:07d}") if common_iteration is not None else None
    comparison["get_up_failure_windows"]={mode:get_up_failures(runs[mode],ev) for mode,ev in finals.items()}
    (result/"comparison.json").write_text(json.dumps(comparison,indent=2)+"\n")
    subprocess.run([sys.executable,"-u",str(ROOT/"scripts/render_goal_videos.py"),str(stage),str(finals["reference_heading"]),str(finals["robot_root"])],check=True)
    shutil.copy2(stage/"videos/video_manifest.json",result/"video_manifest.json")
    stats=(comparison["same_iteration_comparison"] or comparison)["common_prefix_motion_mean"]
    orientation=stats["root_orientation_error_rad"];xy=stats["root_xy_error_m"]
    next_focus=("Relative orientation improved but XY remains unobservable; next study estimated velocity/relative displacement."
        if orientation["B"]<orientation["A"] and xy["B"]>=xy["A"] else
        "Assess matched-input PPO and additional training seeds, guided by remaining actual get-up contact/prediction failures."
        if orientation["B"]<orientation["A"] else
        "Use the actual failure phases and prediction windows to revise the goal/representation choice; retain negative results.")
    summary={"tag":tag,"status":"publishing","runs":statuses,"final_scores":{mode:json.loads((ev/"evaluation.json").read_text()) for mode,ev in finals.items()},
             "common_iteration":common_iteration,"next_focus":next_focus,"pure_XY_unobservable":True,"cleanup":{"deleted":[],"released_bytes":0},"unpublished":[]}
    for score in summary["final_scores"].values():
        score.pop("clips");score.pop("data_definition")
    summary_path=result/"summary.json"
    summary_path.write_text(json.dumps(summary,indent=2)+"\n")
    release_tag="sm-"+tag+"-final"
    notes=stage/"release-notes.md"
    notes.write_text("P2 v2 full joint-training pair, final scoring trajectories and five-class videos.\n\n"+
        "\n".join(f"{mode}: iteration {score['iteration']}, {score['completed_motions']}/40, normalized return {score['mean_normalized_return']:.8f}." for mode,score in summary["final_scores"].items())+
        f"\n\nCommon iteration: {common_iteration}. {next_focus}\n",encoding="utf-8")
    # Training and all milestone/final publication children have exited before this script.
    # Exact existing artifact files form the cleanup whitelist; no parent tree is deleted.
    whitelist=[];coverage={};assets=[]
    for mode,run in runs.items():
        for pub in sorted((ROOT/"outputs/publications").glob("sm-"+run.name+"-i*")):
            if not pub.is_dir():continue
            state=pub/"publication.json"
            if state.exists():
                status=json.loads(state.read_text())
                if status.get("status")=="published":
                    for asset in status["assets"]:
                        coverage[asset["path"]]={"url":asset["url"],"bytes":asset["bytes"]}
                    ev=run/f"evaluation_{status['iteration']:07d}"
                    archive_asset=next(x for x in status["assets"] if x["name"]=="trajectories.tar")
                    for raw in (ev/"trajectories").glob("*.npz"):
                        coverage[str(raw.relative_to(ROOT))]={"url":archive_asset["url"],"member":"trajectories/"+raw.name,"bytes":raw.stat().st_size}
        # Upload the retained initial/recent/final snapshots not already published at milestones.
        for cp in sorted(run.glob("checkpoint_*.pt")):
            if cp.is_symlink():continue
            relative=str(cp.relative_to(ROOT))
            if relative not in coverage:
                renamed=stage/(mode+"-"+cp.name)
                os.link(cp,renamed)
                assets.append(renamed);whitelist.append(cp)
                coverage[relative]={"pending_asset":renamed.name,"bytes":cp.stat().st_size}
    roots=[*runs.values(),stage,ROOT/"outputs/preparation"/tag]
    roots += [p for run in runs.values() for p in (ROOT/"outputs/publications").glob("sm-"+run.name+"-i*") if p.is_dir()]
    extra_logs=[p for run in runs.values() for p in (ROOT/"outputs/publications").glob(run.name+"-i*.log")]
    extra_logs += [ROOT/"outputs/campaigns"/(tag+"-"+mode+".train.log") for mode in runs]
    # Freeze a complete original-record archive after its writers have exited.
    assets += [*sorted((stage/"videos").glob("*.mp4")),stage/"videos/contact_sheet.jpg"]
    record_archive=stage/"original_records.tar"
    with tarfile.open(record_archive,"w") as tar:
        for root in roots:
            for file in sorted(root.rglob("*")):
                if not file.is_file() or file.is_symlink() or file==record_archive or file in assets:continue
                relative=str(file.relative_to(ROOT))
                whitelist.append(file)
                if relative not in coverage:
                    tar.add(file,arcname=relative)
                    coverage[relative]={"pending_asset":record_archive.name,"member":relative,"bytes":file.stat().st_size}
        for file in extra_logs:
            if file.exists():
                relative=str(file.relative_to(ROOT));tar.add(file,arcname=relative);whitelist.append(file)
                coverage[relative]={"pending_asset":record_archive.name,"member":relative,"bytes":file.stat().st_size}
    assets.append(record_archive)
    # Both trainers, all evaluations, failure-window readers and renderers have ended.
    dataset_roots=[ROOT/"data/raw/lafan1_g1",ROOT/"data/processed/lafan1_g1_50hz"]
    dataset_archive=stage/"lafan40_working_data.tar.gz"
    with tarfile.open(dataset_archive,"w:gz") as tar:
        for root in dataset_roots:
            for file in sorted(root.rglob("*")):
                if file.is_file():
                    relative=str(file.relative_to(ROOT));tar.add(file,arcname=relative);whitelist.append(file)
                    coverage[relative]={"pending_asset":dataset_archive.name,"member":relative,"bytes":file.stat().st_size}
    assets.append(dataset_archive);roots.extend(dataset_roots)
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        release=ensure_release(release_tag,"P2 goal feedback / complete pair",notes,git("rev-parse","HEAD"))
        uploaded,missing=upload_files(release_tag,assets,release["id"])
        by_name={x["name"]:x for x in uploaded}
        summary.update(release_url=f"https://github.com/{REPO}/releases/tag/{release_tag}",assets=uploaded,unpublished=missing)
        for relative,record in coverage.items():
            if "pending_asset" in record and record["pending_asset"] in by_name:
                record["url"]=by_name[record["pending_asset"]]["url"]
        summary["upload_inventory"]=coverage
        summary["status"]="uploaded" if not missing else "upload_incomplete"
        summary_path.write_text(json.dumps(summary,indent=2)+"\n")
        def update(index):
            index.setdefault("campaigns",{})[tag]={"status":summary["status"],"summary":str(summary_path.relative_to(ROOT)),"release_url":summary["release_url"]}
            index["next_stage"].update(status=summary["status"],campaign=tag,training_started=True)
        summary["results_commit"]=push_results(release_tag,[result.relative_to(ROOT)],update)
        call(["gh","release","edit",release_tag,"--repo",REPO,"--draft=false","--latest=false","--notes-file",str(notes)])
        # Git push and uploaded name/size confirmations are complete. No consumers remain.
        deleted=[];released=0;seen_inodes=set()
        for file in dict.fromkeys(whitelist+assets):
            if not file.exists() or file.is_symlink():continue
            relative=str(file.relative_to(ROOT));record=coverage.get(relative)
            if file in assets:
                record=by_name.get(file.name)
            if not record or not record.get("url"):continue
            stat=file.stat()
            if stat.st_size!=record["bytes"]:continue
            # Resolve every target within the exact approved run/publication/stage paths.
            resolved=file.resolve()
            if not any(resolved.is_relative_to(root.resolve()) for root in roots) and file not in extra_logs:
                raise ValueError(f"Cleanup target outside P2 paths: {file}")
            inode=(stat.st_dev,stat.st_ino)
            if stat.st_nlink==1 and inode not in seen_inodes:
                released+=stat.st_blocks*512;seen_inodes.add(inode)
            file.unlink();deleted.append({"path":relative,"bytes":stat.st_size})
        for run in runs.values():
            alias=run/"checkpoint_latest.pt"
            if alias.is_symlink() and not alias.exists():alias.unlink()
        summary["cleanup"]={"deleted":deleted,"released_bytes":released,"dataset_cache":"only exact files in data/raw/lafan1_g1 and data/processed/lafan1_g1_50hz, after working-data asset uploaded; upstream LICENSE/README included"}
        summary["status"]="completed" if not missing else "completed_with_unpublished_files"
        summary_path.write_text(json.dumps(summary,indent=2)+"\n")
        push_results(release_tag+"-cleanup",[result.relative_to(ROOT)],update)
    print("P2_COMPLETE",json.dumps({k:v for k,v in summary.items() if k in ("status","release_url","common_iteration","next_focus","unpublished")}),flush=True)

if __name__=="__main__": main()
