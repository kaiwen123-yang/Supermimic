"""Record observed P10 formal progress and publish the actual startup handoff."""
import datetime
import fcntl
import subprocess
from pathlib import Path
from p10_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results


def main():
    p=read(PROTOCOL)
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    campaign=ROOT/"results"/p["campaign"]
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for name,job in p["jobs"].items():
            run=ROOT/"outputs/runs"/job["run"]
            runtime=read(run/"runtime.json")
            budget=read(run/"budget.json")
            import json
            with (run/"metrics.jsonl").open() as f:
                rows=[json.loads(line) for line in f if line.endswith("\n")]
            latest=rows[-1]
            summary=read(campaign/"jobs"/name/"summary.json")
            summary.update(status="running",training_started=True,pid=runtime["pid"],observed_beijing=now,
                observed_training_iteration=latest["iteration"],observed_stage_seconds=budget["stage_elapsed_seconds"],
                observed_new_joint_updates=latest["new_joint_updates"],observed_new_wm_only_updates=latest["new_wm_only_updates"],
                runtime=runtime,latest_training=latest,next_lafan_iteration=12000,next_bones_iteration=15000)
            write(campaign/"jobs"/name/"summary.json",summary)
            write(campaign/"jobs"/name/"actual_config.json",read(run/"config.json"))
            p["jobs"][name]["status"]="running"
        p.update(status="running",implementation_status="implemented_and_formally_running",training_started=True,started_observed_beijing=now)
        write(PROTOCOL,p)
        resources={"observed_beijing":now,"gpu":subprocess.check_output(["nvidia-smi","--query-compute-apps=pid,process_name,used_memory","--format=csv"],text=True),
            "host_memory":{line.split(":")[0]:line.split(":")[1].strip() for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith(("MemTotal:","MemAvailable:"))}}
        write(campaign/"startup_resources.json",resources)
        state=refresh()
        commit=push_results("p10-formal-training-started",[campaign.relative_to(ROOT),PROTOCOL.relative_to(ROOT)],lambda idx:index_update(idx,state))
        print("P10_START_PUBLISHED",commit,flush=True)


if __name__ == "__main__":
    main()
