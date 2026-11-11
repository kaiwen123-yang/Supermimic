"""Publish changed lightweight O2 artifacts without touching another checkout."""
from __future__ import annotations

import argparse
import base64
import fcntl
import json
from pathlib import Path
import re
import subprocess
import time

from common import CAMPAIGN, CODE_ROOT, NODE_ORDER, PUBLICATION_LOCK, RUN_NAME, now, write_json


def github(path, method="GET", data=None):
    command = ["gh", "api", f"repos/kaiwen123-yang/Supermimic/{path}", "--method", method]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=None if data is None else json.dumps(data), text=True,
                            capture_output=True, check=True, timeout=180)
    return json.loads(result.stdout)


def read_blob(sha):
    return base64.b64decode(github(f"git/blobs/{sha}")["content"]).decode()


def refresh(workspace):
    run_dir = workspace / "outputs" / RUN_NAME
    result_dir = workspace / "results" / CAMPAIGN
    stage = json.loads((run_dir / "stage.json").read_text())
    progress = json.loads((run_dir / "progress.json").read_text()) if (run_dir / "progress.json").exists() else None
    nodes = json.loads((run_dir / "nodes.json").read_text()) if (run_dir / "nodes.json").exists() else {}
    evaluations = {label: {source: json.loads((result_dir / "milestones" / label / source / "evaluation.json").read_text())
                          for source in ("bones_full", "lafan40_cross_library")
                          if (result_dir / "milestones" / label / source / "evaluation.json").exists()}
                   for label in NODE_ORDER if label in nodes}
    for label, node in nodes.items():
        completed_sources = list(evaluations.get(label, {}))
        node["evaluation_status"] = ("not_requested" if label == "initial" else "completed" if len(completed_sources) == 2
                                     else "partially_completed" if completed_sources else "pending_after_training_exit")
        node["completed_evaluation_sources"] = completed_sources
    write_json(result_dir / "saved_nodes.json", nodes)
    summary = {"campaign": CAMPAIGN, "run_name": RUN_NAME, "updated_at": now(), "status": stage["status"],
               "implementation_status": "deployed", "plan_commit": "df663ae4872c04f23848aaa528a42fb8cf457f93",
               "data_conversion_started": True, "data_conversion_finished": (result_dir / "data_conversion.json").exists(),
               "stage": stage, "latest_training": progress, "saved_nodes": nodes, "evaluations": evaluations,
               "training_started": progress is not None,
               "training_finished": (run_dir / "training_child_exit.json").exists(),
               "formal_evaluation_started": stage["status"] in {"evaluating_bones", "evaluating_lafan", "completed"},
               "formal_evaluation_finished": bool(evaluations) and all(len(v) == 2 for v in evaluations.values()),
               "initialization": "fresh_seed0_BONES_only", "parent_checkpoint": None, "full_resume": False,
               "budget_seconds": 43200, "max_collection_steps": 1000000, "return_early_stop": None,
               "BONES_count": 130394, "metric_reference": "R>0.90 is SONIC reference; author one-H100 25/129514 failures; member sets not aligned",
               "LAFAN_interpretation": "cross-library evaluation, not O1 forgetting or proven disjoint unseen generalization",
               "previous_lafan_acceptance_preserved": True, "P12": "paused", "large_artifacts": str(run_dir),
               "publication": "included_in_this_commit"}
    write_json(result_dir / "summary.json", summary)
    lines = ["# O2 official full BONES", "", f"Status: **{summary['status']}**. Updated: {summary['updated_at']}.", "",
             "Fresh seed0, BONES-only 130394 clips, official GenCoord/proprio/history10, 4096 environments.",
             "Training ends at cumulative 43200 seconds or 1000000 collections. No return-based early stop.", "",
             "| Node | Library | R | Complete / all | Training seconds |", "|---|---|---:|---:|---:|"]
    for label, by_source in evaluations.items():
        for source, item in by_source.items():
            lines.append(f"| {label} | {source} | {item['mean_normalized_return']:.8f} | {item['completed']}/{item['clip_count']} | {item['checkpoint_metadata']['training_seconds']:.1f} |")
    lines += ["", "Training checkpoints are saved before scoring. A BONES worker scores all saved nodes only after the training child exits; a separate LAFAN40 worker follows.",
              "All scored clips, including failures, are retained in each node's CSV parts. Dataset indices preserve original BONES IDs.",
              "R>0.90 is the SONIC reference. The author's 25 failures use 129514 clips; exact member alignment remains unresolved.",
              "LAFAN is a cross-library evaluation of a BONES-only fresh model. O1 and the existing LAFAN acceptance remain unchanged.",
              "Large weights, packed arrays and full logs remain on D57. No automatic extension, next run, archive or stage cleanup.", ""]
    (result_dir / "README.md").write_text("\n".join(lines))
    if summary["formal_evaluation_finished"]:
        final = evaluations["final"]
        b, l = final["bones_full"], final["lafan40_cross_library"]
        conclusion = ["# O2 bounded segment results", "",
            f"Final BONES R={b['mean_normalized_return']:.8f}; complete {b['completed']}/{b['clip_count']}; failures {b['failed']}.",
            f"R exceeds SONIC 0.90: {b['mean_normalized_return'] > .90}. The author's 25/129514 comparison is not an identical-member benchmark.",
            f"BONES final mean root XY error={b['quality']['root_xy_error_m']:.6f} m. Completion and precise tracking are reported separately.",
            f"LAFAN cross-library R={l['mean_normalized_return']:.8f}, complete {l['completed']}/40.",
            "", "All actual checkpoints and complete per-clip results are retained; comparison files report gained/lost completions and common-complete quality.",
            "These results do not revoke the accepted O1/P6 LAFAN results. No further training budget or P12 was started.", ""]
        (result_dir / "conclusion.md").write_text("\n".join(conclusion))
    return summary


def publish(workspace, label, summary):
    run_dir = workspace / "outputs" / RUN_NAME
    result_dir = workspace / "results" / CAMPAIGN
    ledger_path = run_dir / "published_files.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    files = [(f"results/{CAMPAIGN}/{p.relative_to(result_dir).as_posix()}", p)
             for p in result_dir.rglob("*") if p.is_file() and p.suffix in {".json", ".csv", ".md", ".npz"}]
    files += [(f"scripts/o2/{p.name}", p) for p in (CODE_ROOT / "scripts/o2").iterdir() if p.suffix in {".py", ".sh"}]
    files += [("docs/O2_EXECUTION_HANDOFF.md", CODE_ROOT / "docs/O2_EXECUTION_HANDOFF.md")]
    head = github("git/ref/heads/main")["object"]["sha"]
    base_tree = github(f"git/commits/{head}")["tree"]["sha"]
    entries, marks = [], {}
    for name, path in files:
        stat = path.stat()
        mark = [stat.st_size, stat.st_mtime_ns]
        marks[name] = mark
        if ledger.get(name) == mark:
            continue
        entry = {"path": name, "mode": "100644", "type": "blob"}
        if path.suffix == ".npz" or stat.st_size > 500000:
            blob = github("git/blobs", "POST", {"content": base64.b64encode(path.read_bytes()).decode(), "encoding": "base64"})
            entry["sha"] = blob["sha"]
        else:
            entry["content"] = path.read_text()
        entries.append(entry)
    root_items = {item["path"]: item for item in github(f"git/trees/{base_tree}")["tree"]}
    result_items = {item["path"]: item for item in github(f"git/trees/{root_items['results']['sha']}")["tree"]}
    index = json.loads(read_blob(result_items["index.json"]["sha"]))
    campaign = index["campaigns"][CAMPAIGN]
    for key in ("status", "implementation_status", "training_started", "training_finished", "formal_evaluation_started", "formal_evaluation_finished", "latest_training"):
        campaign[key] = summary[key]
    campaign["runs"][0].update(status=summary["status"], evaluations=summary["evaluations"])
    campaign.update(training_done=summary["training_finished"], full_clip_evaluation_done=summary["formal_evaluation_finished"],
                    lightweight_results_published=True, data_conversion_started=True,
                    publication_scope="actual_O2_execution_and_available_lightweight_results")
    phase = {"preparing": "数据转换与启动准备中", "training": "正式训练已启动", "training_completed_evaluation_pending": "训练已结束，等待评分",
             "evaluating_bones": "训练已结束，正在全BONES评分", "evaluating_lafan": "全BONES评分已结束，正在LAFAN跨库评分",
             "completed": "训练、全部实际节点评分与轻量发布已完成", "failed": "出现实际运行错误，需按记录接续"}[summary["status"]]
    common = (f"{phase}（{summary['status']}）。BONES-only 130394条、seed0从零、4096环境；"
              "累计12h或1000000 collection先到停止，无回报早停。训练子进程退出后依次评分全部实际节点的BONES与LAFAN40。"
              f"状态见results/{CAMPAIGN}/summary.json，接续见docs/O2_EXECUTION_HANDOFF.md。"
              "tmux sm-o2-official-bones-s0；保持活跃状态和累计预算，不重启replay/LR。O1成果保留，P12继续暂停。")
    agents = read_blob(root_items["AGENTS.md"]["sha"])
    agents = re.sub(r"(?m)^- \*\*当前主线O2：.*$", lambda m: "- **当前主线O2：** " + common, agents, count=1)
    agents = re.sub(r"(?m)^## O2官方BONES（.*）$", lambda m: "## O2官方BONES（" + phase + "）", agents, count=1)
    agents = re.sub(r"(?m)^- 当前状态为plan_published_not_started；.*$", lambda m: "- O2已由本轮明确执行授权启动；状态以顶部和campaign summary为准。沿既有官方环境与保留数据执行，O1不重跑，P12暂缓。", agents, count=1)
    readme = read_blob(root_items["README.md"]["sha"])
    readme = re.sub(r"(?m)^> \*\*当前主线：O2.*$", lambda m: "> **当前主线：O2官方完整BONES。** " + common, readme, count=1)
    for name, content in (("AGENTS.md", agents), ("README.md", readme), ("results/index.json", json.dumps(index, indent=2, ensure_ascii=False) + "\n")):
        entries.append({"path": name, "mode": "100644", "type": "blob", "content": content})
    tree = github("git/trees", "POST", {"base_tree": base_tree, "tree": entries})
    commit = github("git/commits", "POST", {"message": f"Publish O2 official BONES {label}", "tree": tree["sha"], "parents": [head]})
    github("git/refs/heads/main", "PATCH", {"sha": commit["sha"], "force": False})
    (workspace / "AGENTS.md").write_text(agents)
    ledger.update(marks)
    write_json(ledger_path, ledger)
    return commit["sha"]


def refresh_and_publish(workspace, label):
    started = time.monotonic()
    summary = refresh(workspace)
    record = workspace / "outputs" / RUN_NAME / f"publication_{label}.json"
    try:
        sha = publish(workspace, label, summary)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        write_json(record, {"status": "failed", "at": now(), "error": str(error), "stderr": error.stderr,
                            "scores_retained": True, "next_action": "retry publication only; do not retrain or rescore"})
        summary["publication"] = "pending_retry"
        if summary["status"] == "completed":
            summary["status"] = "results_complete_publication_pending"
        write_json(workspace / "results" / CAMPAIGN / "summary.json", summary)
        print(f"O2_PUBLICATION_FAILED {label}: {error}", flush=True)
        return None
    write_json(record, {"status": "published", "commit": sha, "at": now(), "publication_seconds": time.monotonic() - started})
    print(f"O2_PUBLISHED {label} {sha}", flush=True)
    return sha


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase")  # historical caller metadata; live stage.json owns lifecycle state
    args = parser.parse_args()
    with PUBLICATION_LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        refresh_and_publish(args.workspace, args.label)
