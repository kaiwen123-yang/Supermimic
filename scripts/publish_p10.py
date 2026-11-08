"""Stage-relative P10 scoring/publication under the existing single lock."""
import argparse
import fcntl
import shutil
import subprocess
import sys
import time
from pathlib import Path
from p10_results import ROOT, PROTOCOL, read, write, refresh, index_update, node_view, paired_comparisons
from p10_metrics import read_score, comparison
from publish_checkpoint import push_results
from finish_tracking_campaign import training_summary


def publish(run_name, iteration, final=False):
    p = read(PROTOCOL)
    run = ROOT/"outputs/runs"/run_name
    cfg = read(run/"config.json")
    name = cfg["job"]
    job = p["jobs"][name]
    final = final or iteration == job["target_iteration"]
    if (run/"status.json").exists():
        final = final or iteration == read(run/"status.json")["iteration"]
    full = final or (iteration-p["evaluation"]["scheduling_origin_iteration"]) % p["evaluation"]["bones_every_new_updates"] == 0
    campaign = ROOT/"results"/p["campaign"]
    jobdir = campaign/"jobs"/name
    result = ROOT/"results"/run_name/"milestones"/f"iteration_{iteration:07d}"
    pubdir = ROOT/"outputs/publications"/f"sm-{run_name}-i{iteration:07d}"
    pubdir.mkdir(parents=True,exist_ok=True)
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if (pubdir/"publication.json").exists():
            previous = read(pubdir/"publication.json")
            if previous["status"] == "published" and (not final or previous["final"]):
                return previous
        result.mkdir(parents=True,exist_ok=True)
        checkpoint = run/f"checkpoint_{iteration:07d}.pt"
        retention = run/f"lafan_retention_{iteration:07d}"
        if not (retention/"evaluation.json").exists():
            with (pubdir/"lafan_retention.log").open("a") as log:
                subprocess.run([sys.executable,"-u",str(ROOT/"scripts/evaluate.py"),str(checkpoint),
                    "--source","lafan","--output-dir",str(retention)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        shutil.copy2(retention/"evaluation.json", result/"lafan_retention.json")
        parent_path = ROOT/p["source"]["evaluation"]
        view = {"iteration":iteration, "stage_updates":iteration-9000, "full_bones_evaluated":full,
            "lafan_retention":node_view(read(parent_path.parent/"lafan_retention.json"),read(retention/"evaluation.json"),
                str((result/"lafan_retention.json").relative_to(ROOT)))}
        if full:
            evaluation = run/f"evaluation_{iteration:07d}"
            if not (evaluation/"evaluation.json").exists():
                args = [sys.executable,"-u",str(ROOT/"scripts/evaluate_bones_p10.py"),str(checkpoint),"--source","bones"]
                if final:
                    args.append("--failure-tails")
                with (pubdir/"evaluation.log").open("a") as log:
                    subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            score = read_score(evaluation/"evaluation.json")
            for part in score["clip_parts"]["parts"]+["clips_index.json","evaluation.json"]:
                shutil.copy2(evaluation/part,result/part)
            view["bones"] = comparison(read_score(parent_path),score,result)
        first = max(9001, 9001+((iteration-9001)//3000)*3000)
        write(result/"training.json",training_summary(run,first,iteration))
        for block in range(((first-1)//1000+1)*1000, ((iteration-1)//1000+1)*1000+1,1000):
            for suffix in ("json","npz"):
                shutil.copy2(run/"training_evidence"/f"interval_{block:07d}.{suffix}",result/f"selected_rollouts_{block:07d}.{suffix}")
        for prefix in ("sampling", "hard_exposure"):
            for path in (run/"training_evidence").glob(prefix+"_*.json"):
                node = int(path.stem.split("_")[-1])
                if first <= node <= iteration:
                    shutil.copy2(path,result/path.name)
        exposure_paths = [path for path in (run/"training_evidence").glob("hard_exposure_*.json")
            if int(path.stem.split("_")[-1]) <= iteration]
        exposure = read(max(exposure_paths))
        view["actual_exposure"] = {key:exposure[key] for key in ("through_iteration","counts","unique_hard_clips_by_phase","unique_hard_reset_bins","WM_errors")}
        write(result/"comparison.json",view)
        for filename in ("config.json","runtime.json"):
            shutil.copy2(run/filename,result/filename)
        resources = {"observed_unix":time.time(), "gpu":subprocess.check_output([
            "nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv"],text=True),
            "host_memory":{line.split(":")[0]:line.split(":")[1].strip() for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith(("MemTotal:","MemAvailable:"))}}
        write(result/"resources.json",resources)
        summary = read(jobdir/"summary.json")
        summary.update(training_started=True, latest_lafan_iteration=iteration,
            latest_lafan=view["lafan_retention"], latest_exposure=view["actual_exposure"],
            latest_publication_iteration=iteration)
        if full:
            summary.update(latest_bones_iteration=iteration,latest_bones={key:score[key] for key in
                ("motions","completed_motions","mean_normalized_return","mean_completion_fraction","quality")})
        write(jobdir/"summary.json",summary)
        paired_comparisons()
        state = refresh()
        publication = {"status":"publishing","run":run_name,"iteration":iteration,"final":final,
            "bones_evaluated":full,"lafan_evaluated":True,"github_release":False,
            "result_url":f"https://github.com/kaiwen123-yang/Supermimic/tree/main/{result.relative_to(ROOT)}"}
        write(result/"publication.json",publication)
        commit = push_results(f"p10-{name}-i{iteration:07d}",[result.relative_to(ROOT),campaign.relative_to(ROOT)],lambda idx:index_update(idx,state))
        publication.update(status="published",results_commit=commit,completed_unix=time.time())
        write(pubdir/"publication.json",publication)
        write(result/"publication.json",publication)
        print("P10_NODE_PUBLISHED",name,iteration,commit,flush=True)
        return publication


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("iteration",type=int)
    parser.add_argument("--final",action="store_true")
    args = parser.parse_args()
    publish(args.run,args.iteration,args.final)
