"""Start the two authorized P7 jobs once; no setup, replay or training restart."""
import datetime
import subprocess
from p7_results import ROOT, PROTOCOL, read, write


def main():
    protocol=read(PROTOCOL)
    result=ROOT/"results"/protocol["campaign"]
    result.mkdir(parents=True,exist_ok=False)
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    jobs={}
    for job in protocol["jobs"]:
        name=job["id"]
        run=ROOT/"outputs/runs"/job["run"]
        summary={"job":name,"run":run.name,"initialization":job["initialization"],"status":"starting",
            "training_started":False,"training_done":False,"full_clip_evaluation_done":False,
            "lightweight_results_published":False,"started_beijing":now,
            "start_iteration":job["start_iteration"],"target_iteration":job["target_iteration"],
            "max_new_stage_hours":16,"tmux_session":"sm-p7-"+name.replace("_","-"),
            "server_run_directory":str(run),"parent":job["parent"],
            "backup_status":"awaiting_user_export_not_confirmed","automatic_stage_cleanup":False}
        write(result/"jobs"/name/"summary.json",summary)
        jobs[name]=summary
    write(result/"summary.json",{"campaign":protocol["campaign"],"status":"starting",
        "training_started":False,"training_done":False,"full_clip_evaluation_done":False,
        "lightweight_results_published":False,"jobs":jobs,"started_beijing":now,
        "study_design":protocol["study_design"],"source_worktree":str(ROOT),
        "publication_lock":str((ROOT/"work/p2-publication.lock").resolve()),
        "evidence_backfill":{"status":"pending"},"backup_status":"awaiting_user_export_not_confirmed",
        "automatic_stage_cleanup":False,"results_url":f"https://github.com/kaiwen123-yang/Supermimic/tree/main/results/{protocol['campaign']}"})
    for job in protocol["jobs"]:
        session=jobs[job["id"]]["tmux_session"]
        subprocess.run(["tmux","new-session","-d","-s",session,"bash "+str(ROOT/"scripts/run_reproduction_d57.sh")+" "+job["id"]],check=True)
        subprocess.run(["tmux","set-option","-t",session,"remain-on-exit","on"],check=True)
        print("P7_DISPATCHED",job["id"],session,flush=True)


if __name__=="__main__":
    main()
