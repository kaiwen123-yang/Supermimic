"""Publish P9 implementation, actual data definition and start evidence once."""
import datetime
import fcntl
import json
import subprocess
from pathlib import Path
from p9_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results
from p9_evidence import export

CODE = ["AGENTS.md", "README.md", "docs/P9_CRITIC_AND_FULL_SCALE_PLAN.md", "docs/P9_CODEX_START_PROMPT.md",
    "configs/next_stage_critic_full_scale_protocol.json", "configs/lafan40_p9_control.json",
    "configs/lafan40_p9_survival_critic.json", "configs/bones_full_lafan_p9_survival.json", "configs/bones_p9_preprocessing.json",
    "supermimic/motion.py", "supermimic/environment.py", "supermimic/learning.py", "supermimic/rollout_evidence.py",
    "scripts/train.py", "scripts/finish_tracking_campaign.py", "scripts/evaluate.py", "scripts/evaluate_bones_p9.py",
    "scripts/start_p9.py", "scripts/run_p9_d57.sh", "scripts/run_p9_bones_pipeline.sh", "scripts/start_p9_bones_when_ready.sh",
    "scripts/prepare_bones_p9.py", "scripts/p9_metrics.py", "scripts/p9_results.py", "scripts/publish_p9.py",
    "scripts/publish_p9_d57.sh", "scripts/finish_p9.py", "scripts/p9_evidence.py", "scripts/publish_p9_data.py"]


def main():
    p = read(PROTOCOL)
    result = ROOT/"results"/p["campaign"]
    evidence = export()
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
        for name,job in p["jobs"].items():
            run = ROOT/"outputs/runs"/job["run"]
            summary_path = result/"jobs"/name/"summary.json"
            summary = read(summary_path)
            if (run/"runtime.json").exists():
                runtime = read(run/"runtime.json")
                rows = []
                if (run/"metrics.jsonl").exists():
                    with (run/"metrics.jsonl").open() as log:
                        rows = [json.loads(line) for line in log if line.endswith("\n")]
                summary.update(status="running" if rows else "initializing", training_started=bool(rows),
                    pid=runtime["pid"], observed_beijing=now,
                    observed_training_iteration=rows[-1]["iteration"] if rows else job["start_iteration"])
                write(result/"jobs"/name/"start_snapshot.json", {"observed_beijing":now,"runtime":runtime,
                    "actual_config":read(run/"config.json"),"first_updates":rows[:6],"latest_update":rows[-1] if rows else None,
                    "scope":"Actual normal training records; formal full-clip evaluations are separate."})
            if name.startswith("bones"):
                summary.update(data_status="completed", data_preparation=read(result/"bones_data/preparation.json"),
                    data_manifest=str(ROOT/"data/processed/bones_full_lafan_p9/manifest.json"))
            write(summary_path,summary)
        evidence["status"] = "published"
        write(result/"evidence/manifest.json",evidence)
        campaign = refresh()
        campaign.update(observed_beijing=now,
            gpu_snapshot=subprocess.check_output(["nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv"],text=True),
            finalization="run_p9_d57.sh -> finish_p9.py: fixed update/accumulated16h endpoint, all formal source-specific scores and Git publication; no P10.")
        write(result/"summary.json",campaign)
        p.update(status="running",training_started=campaign["training_started"])
        prep=read(result/"bones_data/preparation.json")
        p["bones_correction"].update(actual_corrected_count=prep["accepted"],actual_corrected_hours=prep["full_hours"])
        p["execution"].update(observed_beijing=now, jobs={name:j["status"] for name,j in campaign["jobs"].items()})
        write(PROTOCOL,p)
        for relative in ("AGENTS.md","README.md","docs/P9_CRITIC_AND_FULL_SCALE_PLAN.md","docs/P9_CODEX_START_PROMPT.md"):
            path=ROOT/relative
            lines=path.read_text().splitlines()
            if relative=="AGENTS.md":
                lines=[f"- 当前P9已实施并启动，实际状态见results/{p['campaign']}/summary.json。接续既有tmux，不重复启动，不重建活跃replay/LR。" if line.startswith("- 当前入口为P9") else
                    ("## P9实施（已实施，按现有进程继续）" if line.startswith("## P9实施") else line) for line in lines]
            elif relative=="README.md":
                lines=[f"> **当前入口：P9 Critic稳定性与完整库混合训练。** 实际启动/评分状态见[结果索引](results/{p['campaign']}/summary.json)。保持现有tmux和固定预算。" if line.startswith("> **当前入口：") else line for line in lines]
            elif relative.endswith("PLAN.md"):
                lines=[f"状态：**已实施并启动。** 实际三路状态及数据定义见[结果索引](../results/{p['campaign']}/summary.json)；下文保留授权方案。" if line.startswith("状态：") else line for line in lines]
            else:
                lines.insert(2,f"实际状态：P9已实施，先读results/{p['campaign']}/summary.json并检查现有tmux，不要再次运行start_p9.py。")
            path.write_text("\n".join(lines)+"\n")
        subprocess.run(["git","add","--",*CODE],cwd=ROOT,check=True)
        if subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT).returncode:
            subprocess.run(["git","commit","-m","Implement P9 corrected full-library mixed training and bounded source scoring"],cwd=ROOT,check=True)
        commit=push_results("p9-implementation-data-and-start",[Path(x) for x in CODE]+[result.relative_to(ROOT)],lambda index:index_update(index,campaign))
        write(ROOT/"outputs/campaigns/p9-start-publication.json",{"status":"published","commit":commit,"observed_beijing":now})
        print("P9_IMPLEMENTATION_DATA_START_PUBLISHED",commit,flush=True)


if __name__ == "__main__":
    main()
