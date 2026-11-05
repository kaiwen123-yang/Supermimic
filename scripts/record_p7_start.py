"""Publish the observed real P7 startup after both jobs have produced updates."""
import datetime
import fcntl
import json
import subprocess
from p7_results import ROOT, PROTOCOL, read, write, refresh_campaign, update_index
from finish_p7_reproduction import update_documents
from publish_checkpoint import push_results


def main():
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        protocol=read(PROTOCOL)
        result=ROOT/"results"/protocol["campaign"]
        now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
        for job in protocol["jobs"]:
            run=ROOT/"outputs/runs"/job["run"]
            rows=[json.loads(line) for line in (run/"metrics.jsonl").read_text().splitlines(keepends=True) if line.endswith("\n")]
            runtime=read(run/"runtime.json")
            last=rows[-1]
            jobdir=result/"jobs"/job["id"]
            snapshot={"observed_beijing":now,"runtime":runtime,"actual_config":read(run/"config.json"),
                "initial_replay_fill":read(run/"warmup.json"),"first_updates":rows[:6],"latest_update":last,
                "scope":"Startup observation from actual training logs, not formal evaluation."}
            write(jobdir/"start_snapshot.json",snapshot)
            summary=read(jobdir/"summary.json")
            summary.update(status="running",training_started=True,pid=runtime["pid"],observed_beijing=now,
                observed_training_iteration=last["iteration"],observed_new_actor_updates=last["new_actor_updates"],
                observed_new_wm_only_updates=last["new_wm_only_updates"],previous_elapsed_seconds=runtime["previous_elapsed_seconds"],
                evaluation_iterations=job["evaluation_iterations"],tail_iterations=job["tail_iterations"],
                actor_encoder_input_dimensions=713,actor_learning_rate_scale=.5,
                question=job["question"],start_snapshot=str((jobdir/"start_snapshot.json").relative_to(ROOT)))
            write(jobdir/"summary.json",summary)
        campaign=read(result/"summary.json")
        campaign.update(status="running",training_started=True,observed_beijing=now,
            implementation_commit=runtime["git_commit"],
            gpu_snapshot=subprocess.check_output(["nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv"],text=True),
            gpu_snapshot_scope="Startup observation only; shared GPU and no exclusivity.",
            torch_threads_per_training_and_evaluation=2,
            finalization="Each job runs finish_p7_reproduction.py at endpoint or 16h cap; evaluations/publication and six WM windows share one lock.",
            interaction_handoff="Continue existing tmux jobs; no replay/LR restart. Endpoints42000/9000; no automatic extension/P8.")
        write(result/"summary.json",campaign)
        campaign=refresh_campaign(protocol)
        protocol.update(status="running",implementation_status="implemented",training_started=True)
        protocol["implementation"]["planned_only"]=False
        protocol["execution"].update(status="running",actual_configs_created=True,training_started=True,
            plan_and_review_only=False,started_beijing=campaign["started_beijing"],observed_beijing=now,
            jobs={j["id"]:"running" for j in protocol["jobs"]})
        write(PROTOCOL,protocol)
        paths=[result.relative_to(ROOT),PROTOCOL.relative_to(ROOT),*update_documents(campaign)]
        commit=push_results("p7-formal-training-started",paths,lambda index:update_index(index,campaign))
        print("P7_START_PUBLISHED",commit,now,flush=True)


if __name__=="__main__":
    main()
