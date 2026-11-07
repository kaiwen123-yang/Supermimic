"""One observed startup record, published after the current formal score releases the lock."""
import datetime
import fcntl
import json
from pathlib import Path
from p9_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results, git


def main():
    p=read(PROTOCOL)
    result=ROOT/"results"/p["campaign"]
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    observed={"observed_beijing":now,"jobs":{},"scope":"Observed normal updates; no extra inference or tests."}
    for name,job in p["jobs"].items():
        run=ROOT/"outputs/runs"/job["run"]
        with (run/"metrics.jsonl").open() as log:
            rows=[json.loads(line) for line in log if line.endswith("\n")]
        observed["jobs"][name]={"tmux":job["tmux"],"run":job["run"],"runtime":read(run/"runtime.json"),
            "actual_config":read(run/"config.json"),"first_six_updates":rows[:6],"latest_observed_update":rows[-1],
            "server_run_directory":str(run)}
    write(ROOT/"outputs/campaigns/p9-all-started-observation.json",observed)
    print("P9_ALL_THREE_JOINT_TRAINING_OBSERVED",now,flush=True)
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        paths=[]
        for name,record in observed["jobs"].items():
            jobdir=result/"jobs"/name
            write(jobdir/"start_snapshot.json",record)
            summary=read(jobdir/"summary.json")
            summary.update(training_started=True, pid=record["runtime"]["pid"], observed_beijing=now,
                observed_training_iteration=record["latest_observed_update"]["iteration"])
            if not summary.get("training_done"):
                summary["status"]="running"
            write(jobdir/"summary.json",summary)
            paths.extend([(jobdir/"summary.json").relative_to(ROOT),(jobdir/"start_snapshot.json").relative_to(ROOT)])
        campaign=refresh()
        paths += [(result/"summary.json").relative_to(ROOT),Path("scripts/record_p9_started.py"),Path("scripts/record_p9_started_d57.sh")]
        # Preserve the actual two deployment commits used by the already-running processes.
        git("push","origin","HEAD:refs/heads/codex/p9-critic-full-scale")
        commit=push_results("p9-three-joint-training-confirmed",paths,lambda index:index_update(index,campaign))
        write(ROOT/"outputs/campaigns/p9-all-started-publication.json",{"status":"published","commit":commit,"observed_beijing":now})
        print("P9_ALL_STARTED_PUBLISHED",commit,flush=True)


if __name__=="__main__":
    main()
