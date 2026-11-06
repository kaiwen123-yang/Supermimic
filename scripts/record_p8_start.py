"""Publish observed P8 updates and implementation, without interrupting training."""
import datetime
import fcntl
import json
import subprocess
from pathlib import Path
from p8_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results


def main():
    protocol = read(PROTOCOL)
    result = ROOT / "results" / protocol["campaign"]
    with Path(protocol["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
        for name, job in protocol["jobs"].items():
            run = ROOT / "outputs/runs" / job["run"]
            jobdir = result / "jobs" / name
            summary = read(jobdir / "summary.json")
            if (run / "metrics.jsonl").exists():
                with (run / "metrics.jsonl").open() as log:
                    rows = [json.loads(line) for line in log if line.endswith("\n")]
                runtime = read(run / "runtime.json")
                write(jobdir / "start_snapshot.json", {"observed_beijing": now, "runtime": runtime,
                    "actual_config": read(run / "config.json"), "initial_replay_fill": read(run / "warmup.json"),
                    "first_updates": rows[:6], "latest_update": rows[-1], "scope": "Actual training records, not full-clip evaluation"})
                summary.update(status="running", training_started=True, pid=runtime["pid"], observed_beijing=now,
                    observed_training_iteration=rows[-1]["iteration"], observed_new_joint_updates=rows[-1]["new_joint_updates"],
                    stage_elapsed_seconds=rows[-1]["stage_elapsed_seconds"],
                    previous_elapsed_seconds=runtime["previous_elapsed_seconds"])
            elif name == "bones40_transfer_h32":
                acquisition = read(result / "bones_data/acquisition.json")
                summary.update(status=acquisition["status"], data_status=acquisition["status"])
            write(jobdir / "summary.json", summary)
        campaign = refresh()
        campaign["gpu_snapshot"] = subprocess.check_output(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv"], text=True)
        campaign["observed_beijing"] = now
        campaign["finalization"] = "run_p8_d57.sh invokes finish_p8.py after target/cumulative16h; all formal scoring/evidence/publication uses protocol lock."
        write(result / "summary.json", campaign)
        protocol.update(status=campaign["status"], training_started=True)
        protocol["execution"].update(observed_beijing=now, jobs={n: j["status"] for n, j in campaign["jobs"].items()})
        write(PROTOCOL, protocol)
        for relative in ("AGENTS.md", "docs/P8_STABILITY_AND_SCALE_PLAN.md", "docs/P8_CODEX_START_PROMPT.md", "README.md"):
            path = ROOT / relative
            lines = path.read_text().splitlines()
            if relative == "AGENTS.md":
                lines = [f"- 当前入口为P8：docs/P8_STABILITY_AND_SCALE_PLAN.md、configs/next_stage_stability_scale_protocol.json、docs/P8_CODEX_START_PROMPT.md。P8两路LAFAN已从C42000正式联合更新；BONES按实际数据状态继续，见results/{protocol['campaign']}/summary.json。接续已有tmux，不重复启动P7/P8，不重建活跃replay或重置LR。" if line.startswith("- 当前入口为P8：") else ("## P8实施（LAFAN正式训练已启动，BONES按实际数据状态推进）" if line.startswith("## P8实施") else line) for line in lines]
            elif relative.endswith("P8_STABILITY_AND_SCALE_PLAN.md"):
                lines = [f"状态：**两路LAFAN正式训练已启动，BONES按实际数据状态推进。** 实际运行与数据状态见[结果索引](../results/{protocol['campaign']}/summary.json)。下文保留已授权的固定预算。" if line.startswith("状态：") else line for line in lines]
            elif relative == "README.md":
                lines = [f"> **当前入口：P8稳定性与规模训练。** LAFAN H32/H16已从C42000正式联合更新，BONES依已获准的官方数据推进；实际状态见[结果索引](results/{protocol['campaign']}/summary.json)。接续既有tmux，不重复启动。" if line.startswith("> **当前入口：") else line for line in lines]
            else:
                marker = f"实际状态：P8已开始执行。先读results/{protocol['campaign']}/summary.json并检查已有tmux，再处理未完任务；不要再次运行start_p8.py。"
                if marker not in lines:
                    lines.insert(2, marker)
            path.write_text("\n".join(lines)+"\n")
        code_paths = [Path(p) for p in subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).splitlines()]
        code_paths += [Path(p) for p in subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "scripts", "configs"], cwd=ROOT, text=True).splitlines()]
        subprocess.run(["git", "add", "--", *map(str, code_paths)], cwd=ROOT, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
            subprocess.run(["git", "commit", "-m", "Implement P8 bounded H32/H16 continuation and BONES scale paths"], cwd=ROOT, check=True)
        code_paths += [Path(p) for p in subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=ROOT, text=True).splitlines()]
        paths = sorted(set(code_paths + [result.relative_to(ROOT)]))
        commit = push_results("p8-formal-training-started", paths, lambda index: index_update(index, campaign))
        print("P8_START_PUBLISHED", now, commit, flush=True)


if __name__ == "__main__":
    main()
