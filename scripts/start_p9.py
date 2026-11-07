"""Dispatch the authorized P9 LAFAN jobs in their own tmux sessions."""
import datetime
import subprocess
from p9_results import ROOT, PROTOCOL, read, write, refresh


def main():
    protocol = read(PROTOCOL)
    result = ROOT / "results" / protocol["campaign"]
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    for name, job in protocol["jobs"].items():
        write(result / "jobs" / name / "summary.json", {"job": name, "run": job["run"],
            "tmux": job["tmux"], "status": "starting" if name.startswith("lafan") else "preparing_corrected_full_library",
            "training_started": False, "training_done": False, "full_clip_evaluation_done": False,
            "lightweight_results_published": False, "initialization": job["initialization"],
            "start_iteration": job["start_iteration"], "target_iteration": job["target_iteration"],
            "max_accumulated_stage_hours": 16, "started_beijing": now if name.startswith("lafan") else None,
            "source_checkpoint": protocol["source"]["checkpoint"], "server_run_directory": str(ROOT / "outputs/runs" / job["run"]),
            "backup_status": "awaiting_user_export_not_confirmed"})
    refresh()
    for name in ("lafan_h32_control", "lafan_h32_survival_critic"):
        job = protocol["jobs"][name]
        subprocess.run(["tmux", "new-session", "-d", "-s", job["tmux"], "bash " + str(ROOT / "scripts/run_p9_d57.sh") + " " + name], check=True)
        subprocess.run(["tmux", "set-option", "-t", job["tmux"], "remain-on-exit", "on"], check=True)
        print("P9_DISPATCHED", name, job["tmux"], flush=True)


if __name__ == "__main__":
    main()
