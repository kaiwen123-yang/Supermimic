"""Publish formal evaluation and training records to Git; bulk artifacts stay on D57."""
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
import traceback
ROOT=Path(__file__).resolve().parents[1]
REPO="kaiwen123-yang/Supermimic"
URL=f"https://github.com/{REPO}.git"
# P3 milestone publication hit repeated TLS timeouts through academic acceleration.
# Use the existing D57 proxy for GitHub requests without changing training's environment.
GH_ENV=os.environ.copy()
GH_ENV.update({key:"http://127.0.0.1:7890" for key in
               ("HTTPS_PROXY","HTTP_PROXY","ALL_PROXY","https_proxy","http_proxy","all_proxy")})


def call(args,cwd=ROOT):
    r=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=GH_ENV)
    if r.returncode:
        raise RuntimeError(f"{args[0]} failed ({r.returncode}): {r.stderr[-4000:]}")
    return r.stdout.strip()


def git(*args,cwd=ROOT):
    return call(["git","-c","credential.helper=","-c","credential.helper=!gh auth git-credential",
                 "-c","http.proxy=http://127.0.0.1:7890",*args],cwd)


def release_by_tag(tag,release_id=None):
    rid=release_id if release_id is not None else json.loads(call(["gh","release","view",tag,"--repo",REPO,"--json","databaseId"]))["databaseId"]
    return json.loads(call(["gh","api",f"repos/{REPO}/releases/{rid}"]))


def ensure_release(tag,title,notes,commit):
    existing=subprocess.run(["gh","release","view",tag,"--repo",REPO,"--json","databaseId"],capture_output=True,text=True,env=GH_ENV)
    if existing.returncode:
        created=json.loads(call(["gh","api",f"repos/{REPO}/releases","--method","POST",
            "-f",f"tag_name={tag}","-f",f"target_commitish={commit}","-f",f"name={title}","-F","draft=false","-F",f"body=@{notes}"]))
        return release_by_tag(tag,created["id"])
    release=release_by_tag(tag,json.loads(existing.stdout)["databaseId"])
    if release["draft"]:
        call(["gh","release","edit",tag,"--repo",REPO,"--draft=false","--latest=false"])
        release=release_by_tag(tag,release["id"])
    return release


def upload_files(tag,paths,release_id=None):
    remote={a["name"]:a for a in release_by_tag(tag,release_id)["assets"]}
    uploaded,missing=[],[]
    for path in paths:
        size=path.stat().st_size
        asset=remote.get(path.name)
        try:
            if not (asset and asset["state"]=="uploaded" and asset["size"]==size):
                call(["gh","release","upload",tag,str(path),"--repo",REPO,"--clobber"])
                asset=next(a for a in release_by_tag(tag,release_id)["assets"] if a["name"]==path.name)
            if asset["state"]!="uploaded" or asset["size"]!=size:
                raise RuntimeError(f"Asset not fully uploaded: {path.name}")
            uploaded.append({"path":str(path.relative_to(ROOT)),"name":path.name,"bytes":size,
                             "state":asset["state"],"url":asset["browser_download_url"],"network":"D57 existing localhost HTTP proxy"})
            print("ASSET_UPLOADED",path.name,size,flush=True)
        except Exception as exc:
            missing.append({"path":str(path.relative_to(ROOT)),"bytes":size,"error":str(exc)})
            print("ASSET_UPLOAD_FAILED",path.name,str(exc),flush=True)
    return uploaded,missing


def archive_parts(path):
    """Ordered byte parts of a completed tar stream, each at most 1 GiB."""
    limit=1024**3
    if path.stat().st_size<=limit:
        return [path]
    parts=[]
    with path.open("rb") as source:
        for number in range((path.stat().st_size+limit-1)//limit):
            part=path.with_name(path.name+f".part{number+1:03d}")
            remaining=min(limit,path.stat().st_size-number*limit)
            with part.open("wb") as output:
                while remaining:
                    block=source.read(min(8*1024**2,remaining))
                    output.write(block);remaining-=len(block)
            parts.append(part)
    return parts


def push_results(tag,relative_paths,index_update):
    git("fetch",URL,"main")
    worktree=ROOT.parent/"supermimic-publications"/(tag+"-"+str(time.time_ns()))
    worktree.parent.mkdir(exist_ok=True)
    git("worktree","add","--detach",str(worktree),git("rev-parse","FETCH_HEAD"))
    for relative in relative_paths:
        source=ROOT/relative
        destination=worktree/relative
        if source.is_dir():
            shutil.copytree(source,destination,dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
    ip=worktree/"results/index.json"
    index=json.loads(ip.read_text())
    index_update(index)
    ip.write_text(json.dumps(index,indent=2,ensure_ascii=False)+"\n")
    git("add","--",*[str(p) for p in relative_paths],"results/index.json",cwd=worktree)
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=worktree).returncode:
        git("commit","-m",f"Record SuperMimic {tag}",cwd=worktree)
    commit=git("rev-parse","HEAD",cwd=worktree)
    git("push",URL,"HEAD:main",cwd=worktree)
    return commit


def publish(run_name,iteration,final=False):
    """Evaluate once, then publish JSON/JSONL to Git; retain large files on D57."""
    run=ROOT/"outputs/runs"/run_name
    tag=f"sm-{run_name}-i{iteration:07d}"
    pub=ROOT/"outputs/publications"/tag
    pub.mkdir(parents=True,exist_ok=True)
    sp=pub/"publication.json"
    result=ROOT/"results"/run_name/"milestones"/f"iteration_{iteration:07d}"
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if sp.exists() and json.loads(sp.read_text()).get("status")=="published":
            status=json.loads(sp.read_text())
            if final and not status.get("final",False):
                status["final"]=True
                (result/"publication.json").write_text(json.dumps(status,indent=2)+"\n")
                def mark_final(index):
                    index["publications"][tag].update(status="published",final=True)
                status["final_metadata_commit"]=push_results(tag+"-final-metadata",[result.relative_to(ROOT)],mark_final)
                sp.write_text(json.dumps(status,indent=2)+"\n")
            return status
        status={"run":run_name,"iteration":iteration,"tag":tag,"status":"preparing",
                "started_unix":time.time(),"publication_policy":"lightweight_git_first_bulk_artifacts_local"}
        sp.write_text(json.dumps(status,indent=2)+"\n")
        try:
            checkpoint=run/f"checkpoint_{iteration:07d}.pt"
            cfg=json.loads((run/"config.json").read_text())
            campaign=cfg["campaign"]
            evaluation_dir=run/f"evaluation_{iteration:07d}"
            if not (evaluation_dir/"evaluation.json").exists():
                with (pub/"evaluation.log").open("a") as log:
                    subprocess.run([sys.executable,"-u",str(ROOT/"scripts/evaluate.py"),str(checkpoint)],
                                   cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            evaluation=json.loads((evaluation_dir/"evaluation.json").read_text())
            result.mkdir(parents=True,exist_ok=True)
            for name in ("config.json","runtime.json"):
                shutil.copy2(run/name,result/name)
            shutil.copy2(evaluation_dir/"evaluation.json",result/"evaluation.json")
            lines=[line for line in (run/"metrics.jsonl").read_text().splitlines(keepends=True)
                   if line.endswith("\n") and json.loads(line)["iteration"]<=iteration]
            training_path=ROOT/"results"/run_name/"training.jsonl"
            training_path.write_text("".join(lines))
            (result/"training.json").write_text(json.dumps(json.loads(lines[-1]),indent=2)+"\n")
            # The existing finalizer provides the same per-motion comparison at every node.
            from finish_c0_continuation import compare_to_parent
            protocol=json.loads((ROOT/"configs/next_stage_continuation_protocol.json").read_text())
            parent=json.loads((ROOT/protocol["parent"]["evaluation"]).read_text())
            comparison=compare_to_parent(parent,evaluation)
            comparison["conclusion"]=(f"Iteration {iteration}: {evaluation['completed_motions']}/40 complete; "
                f"full-duration normalized return {evaluation['mean_normalized_return']:.8f}; "
                f"retained {len(comparison['parent_successes_retained'])}/29 parent successes, "
                f"completed {len(comparison['newly_completed'])}/11 parent failures. "
                "One fixed checkpoint; no convergence or unseen-motion generalization claim.")
            (result/"comparison.json").write_text(json.dumps(comparison,indent=2)+"\n")
            summary_path=ROOT/"results"/campaign/"summary.json"
            summary=json.loads(summary_path.read_text())
            summary.update(publication_policy=status["publication_policy"],latest_evaluated_iteration=iteration,
                latest_evaluation={key:evaluation[key] for key in ("completed_motions","mean_normalized_return","mean_completion_fraction")},
                latest_parent_successes_retained=len(comparison["parent_successes_retained"]),
                latest_newly_completed=comparison["newly_completed"],
                server_artifacts={"worktree":str(ROOT),"run_directory":str(run),
                    "checkpoint":str(checkpoint),"checkpoint_purpose":"model/optimizer/sampler/RNG for continuation",
                    "parent_checkpoint":str(ROOT/"outputs/parents"/campaign/"checkpoint_0009000.pt"),
                    "trajectories":str(evaluation_dir/"trajectories"),"trajectory_purpose":"full evaluation scoring and on-demand video",
                    "processed_cache":str(ROOT/"data/processed/lafan1_g1_50hz"),
                    "logs":str(ROOT/"outputs/campaigns"/(run_name+".train.log")),
                    "still_in_use":["run checkpoints","parent checkpoint","processed motion cache","training log"],
                    "backup_status":"awaiting_user_export_not_confirmed","deletion_owner":"user"},
                bulk_artifacts_status="retained_on_server_by_policy",unpublished=[])
            summary_path.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
            result_url=f"https://github.com/{REPO}/tree/main/{result.relative_to(ROOT).as_posix()}"
            status.update(status="published",goal_frame=cfg["goal_frame"],
                world_termination_loss=cfg.get("world_termination_loss","aux_bce"),
                completed_motions=evaluation["completed_motions"],mean_normalized_return=evaluation["mean_normalized_return"],
                result_url=result_url,final=final,full_clip_evaluation_done=True,assets=[],unpublished=[],
                bulk_artifacts_status="retained_on_server_by_policy",backup_status="awaiting_user_export_not_confirmed",automatic_cleanup=False)
            (result/"publication.json").write_text(json.dumps(status,indent=2)+"\n")
            def update(index):
                index.setdefault("publications",{})[tag]={key:status[key] for key in
                    ("iteration","goal_frame","world_termination_loss","result_url","status","completed_motions","mean_normalized_return","final","publication_policy")}
                index["next_stage"].update(status="running",training_started=True,campaign=campaign,
                    publication_policy=status["publication_policy"],latest_evaluated_iteration=iteration)
                index["campaigns"][campaign].update(latest_evaluated_iteration=iteration,publication_policy=status["publication_policy"],
                    bulk_artifacts_status="retained_on_server_by_policy",server_run_directory=str(run),backup_status="awaiting_user_export_not_confirmed")
            commit=push_results(tag,[result.relative_to(ROOT),training_path.relative_to(ROOT),summary_path.relative_to(ROOT)],update)
            status.update(results_commit=commit,completed_unix=time.time())
            sp.write_text(json.dumps(status,indent=2)+"\n")
            print("MILESTONE_LIGHTWEIGHT_PUBLISHED",json.dumps(status),flush=True)
            return status
        except Exception as exc:
            status.update(status="failed",error=repr(exc),traceback=traceback.format_exc())
            sp.write_text(json.dumps(status,indent=2)+"\n")
            raise


def main():
    p=argparse.ArgumentParser();p.add_argument("run");p.add_argument("iteration",type=int);p.add_argument("--final",action="store_true")
    a=p.parse_args();publish(a.run,a.iteration,a.final)

if __name__=="__main__": main()
