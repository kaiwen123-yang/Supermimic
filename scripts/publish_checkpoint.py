"""Publish one fixed evaluation/checkpoint using Git and uploaded asset names/sizes."""
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
    run=ROOT/"outputs/runs"/run_name
    tag=f"sm-{run_name}-i{iteration:07d}"
    pub=ROOT/"outputs/publications"/tag
    pub.mkdir(parents=True,exist_ok=True)
    sp=pub/"publication.json"
    status={"run":run_name,"iteration":iteration,"tag":tag,"status":"preparing","started_unix":time.time()}
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if sp.exists() and json.loads(sp.read_text()).get("status")=="published":
            status=json.loads(sp.read_text())
            if final and not status.get("final",False):
                status["final"]=True
                result=ROOT/"results"/run_name/"milestones"/f"iteration_{iteration:07d}"
                (result/"publication.json").write_text(json.dumps(status,indent=2)+"\n")
                def mark_final(index):
                    index["publications"][tag].update(status="published",final=True)
                status["final_metadata_commit"]=push_results(tag+"-final-metadata",[result.relative_to(ROOT)],mark_final)
                sp.write_text(json.dumps(status,indent=2)+"\n")
            return status
        sp.write_text(json.dumps(status,indent=2)+"\n")
        try:
            checkpoint=run/f"checkpoint_{iteration:07d}.pt"
            cfg=json.loads((run/"config.json").read_text())
            campaign=cfg.get("campaign", "20261101-goal-feedback-s0")
            arm=cfg.get("arm", cfg["goal_frame"])
            runtime=json.loads((run/"runtime.json").read_text())
            evaluation_dir=run/f"evaluation_{iteration:07d}"
            if not (evaluation_dir/"evaluation.json").exists():
                with (pub/"evaluation.log").open("a") as log:
                    subprocess.run([sys.executable,"-u",str(ROOT/"scripts/evaluate.py"),str(checkpoint)],
                                   cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            evaluation=json.loads((evaluation_dir/"evaluation.json").read_text())
            result=ROOT/"results"/run_name/"milestones"/f"iteration_{iteration:07d}"
            result.mkdir(parents=True,exist_ok=True)
            for name in ("config.json","runtime.json"):
                shutil.copy2(run/name,result/name)
            shutil.copy2(evaluation_dir/"evaluation.json",result/"evaluation.json")
            rows=[json.loads(line) for line in (run/"metrics.jsonl").read_text().splitlines() if line]
            rows=[r for r in rows if r["iteration"]<=iteration]
            (result/"training.json").write_text(json.dumps(rows[-1],indent=2)+"\n")
            archive=pub/"trajectories.tar"
            if not archive.exists():
                with tarfile.open(archive,"w") as tar:
                    tar.add(evaluation_dir/"trajectories",arcname="trajectories")
            notes=pub/"release-notes.md"
            notes.write_text(f"{campaign} / {arm}, seed 0, iteration {iteration}.\n\n"
                f"Completed {evaluation['completed_motions']}/40; full-duration normalized return {evaluation['mean_normalized_return']:.8f}. "
                "All motions and failed tails remain in the denominator. Raw state/reference/action/reward trajectories are the scoring source.\n\n"
                f"Training source: {runtime['git_commit']}. Full model and optimizer checkpoint included. "
                f"World termination training objective: {cfg.get('world_termination_loss', 'aux_bce')}. "
                "Stage observations do not establish convergence; tracking coverage is an additional diagnostic.\n",encoding="utf-8")
            release=ensure_release(tag,f"{arm} / iteration {iteration}",notes,runtime["git_commit"])
            parts=archive_parts(archive)
            uploaded,missing=upload_files(tag,[checkpoint,*parts,pub/"evaluation.log",*(result/n for n in ("evaluation.json","config.json","runtime.json","training.json"))],release["id"])
            status.update(status="assets_uploaded" if not missing else "upload_incomplete",assets=uploaded,unpublished=missing,
                          goal_frame=cfg["goal_frame"],world_termination_loss=cfg.get("world_termination_loss", "aux_bce"),
                          trajectory_archive_parts=[p.name for p in parts],completed_motions=evaluation["completed_motions"],
                          mean_normalized_return=evaluation["mean_normalized_return"],
                          release_url=f"https://github.com/{REPO}/releases/tag/{tag}",final=final)
            call(["gh","release","edit",tag,"--repo",REPO,"--draft=false","--latest=false"])
            status["status"]="published" if not missing else "upload_incomplete"
            (result/"publication.json").write_text(json.dumps(status,indent=2)+"\n")
            def update(index):
                index.setdefault("publications",{})[tag]={k:status[k] for k in ("iteration","goal_frame","world_termination_loss","release_url","status","completed_motions","mean_normalized_return","final")}
                index["next_stage"].update(status="running",training_started=True,campaign=campaign)
            commit=push_results(tag,[result.relative_to(ROOT)],update)
            status.update(status="published" if not missing else "upload_incomplete",results_commit=commit,completed_unix=time.time())
            sp.write_text(json.dumps(status,indent=2)+"\n")
            print("MILESTONE_PUBLISHED",json.dumps(status),flush=True)
            return status
        except Exception as exc:
            status.update(status="failed",error=repr(exc),traceback=traceback.format_exc())
            sp.write_text(json.dumps(status,indent=2)+"\n")
            raise


def main():
    p=argparse.ArgumentParser();p.add_argument("run");p.add_argument("iteration",type=int);p.add_argument("--final",action="store_true")
    a=p.parse_args();publish(a.run,a.iteration,a.final)

if __name__=="__main__": main()
