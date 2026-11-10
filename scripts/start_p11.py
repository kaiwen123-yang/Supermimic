"""Dispatch one authorized real P11 job after the previous job enters learning."""
import argparse
import datetime
import shlex
import subprocess
from p11_results import ROOT, PROTOCOL, read, write, refresh


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("job",choices=("full8k_residual_control","full8k_velocity_height"))
    name=parser.parse_args().job
    p=read(PROTOCOL)
    result=ROOT/"results"/p["campaign"]
    for key,job in p["jobs"].items():
        path=result/"jobs"/key/"summary.json"
        if not path.exists():
            write(path,{"job":key,"run":job["run"],"tmux":job["tmux"],"status":"ready",
                "training_started":False,"training_done":False,"full_clip_evaluation_done":False,"lightweight_results_published":False,
                "initialization":"full_resume","start_iteration":27000,"target_iteration":36000,"max_accumulated_stage_hours":20,"world_root_height_mode":job["world_root_height_mode"],
                "source_checkpoint":p["parent"]["checkpoint"],"server_run_directory":str(ROOT/"outputs/runs"/job["run"]),
                "backup_status":"awaiting_user_export_not_confirmed"})
    job=p["jobs"][name]
    command=shlex.join(["bash",str(ROOT/"scripts/run_p11_d57.sh"),name])
    subprocess.run(["tmux","new-session","-d","-s",job["tmux"],command],check=True)
    subprocess.run(["tmux","set-option","-t",job["tmux"],"remain-on-exit","on"],check=True)
    path=result/"jobs"/name/"summary.json"
    summary=read(path)
    summary.update(status="starting",started_beijing=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat())
    write(path,summary)
    refresh()
    print("P11_DISPATCHED",name,job["tmux"],flush=True)


if __name__ == "__main__":
    main()
