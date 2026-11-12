"""Serial process boundaries enforce train -> BONES -> LAFAN -> publication."""
import argparse
import fcntl
from pathlib import Path
import subprocess
import sys

from common import CAMPAIGN, PUBLICATION_LOCK, RUN_NAME, now, write_json
from publish_results import refresh_and_publish


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--start-at", choices=("prepare", "bones", "lafan", "publish"), default="prepare")
    args = parser.parse_args()
    run = args.workspace / "outputs" / RUN_NAME
    run.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).parent

    def stage(status):
        write_json(run / "stage.json", {"status": status, "at": now(), "driver_pid": __import__("os").getpid()})

    def child(script, *extra):
        with (run / f"{script}.log").open("a") as stream:
            process = subprocess.Popen([sys.executable, str(scripts / f"{script}.py"), "--workspace", str(args.workspace), *extra],
                                       stdout=stream, stderr=subprocess.STDOUT)
            write_json(run / "active_child.json", {"script": script, "pid": process.pid, "started_at": now()})
            code = process.wait()
        if code:
            stage("failed")
            publish(f"{script}-failed")
            raise RuntimeError(f"{script} exited {code}; saved artifacts and budget retained")
        return process.pid

    def publish(label):
        with PUBLICATION_LOCK.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return refresh_and_publish(args.workspace, label)

    if args.start_at == "prepare":
        stage("preparing")
        child("pack_existing_bones")
        publish("data-ready")
        stage("training")
        pid = child("train_official")  # wait() must return before a scoring worker exists
        exit_record = {"status": "exited", "pid": pid, "exit_code": 0, "observed_exit_at": now()}
        write_json(run / "training_child_exit.json", exit_record)
        write_json(args.workspace / "results" / CAMPAIGN / "training_child_exit.json", exit_record)
        stage("training_completed_evaluation_pending")
        publish("training-exited")
    if args.start_at in {"prepare", "bones"}:
        stage("evaluating_bones")
        publish("bones-scoring-start")
        child("evaluate_library", "--source", "bones_full")
    if args.start_at in {"prepare", "bones", "lafan"}:
        stage("evaluating_lafan")
        publish("lafan-scoring-start")
        child("evaluate_library", "--source", "lafan40_cross_library")
    stage("completed")
    publish("completed")


if __name__ == "__main__":
    main()
