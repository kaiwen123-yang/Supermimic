"""O6 identities and collection-budget state; shared O3 metric definitions."""
from __future__ import annotations
import csv
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = "20261116-o6-official-adam-cosine-s0"
RUN_NAME = "o6-bones-adam-cosine-s0"
SOURCE_NAME = "supermimic-o6-adam-cosine"
PLAN_COMMIT = "b86cb9abdfce21fbc9b53195024da2042b8f6a26"
TASK = "SuperMimic-GenCoord-G1"
CODE_ROOT = Path("/root/autodl-tmp/robot-repro/supermimic-o6-official-adam-cosine")
PROTOCOL_PATH = CODE_ROOT / "configs/o6_official_adam_cosine_protocol.json"
PUBLICATION_LOCK = Path("/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock")
COLLECTION_LIMIT = 320000
CHECKPOINT_COLLECTIONS = (80000, 160000, 250000, 320000)
NODE_ORDER = tuple(f"collection_{n:06d}" for n in CHECKPOINT_COLLECTIONS) + ("final",)
sys.path.append(str(CODE_ROOT / "scripts/o3"))
QUALITY = ("root_position_error_m", "root_xy_error_m", "root_z_absolute_error_m",
           "root_orientation_error_rad", "relative_body_position_error_m", "relative_body_orientation_error_rad")


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def training_state(workspace):
    campaign = workspace / "outputs" / CAMPAIGN
    progress = read_json(workspace / "outputs" / RUN_NAME / "progress.json", {})
    child = read_json(campaign / "training_child.json")
    exited = read_json(campaign / "training_child_exit.json")
    collections = progress.get("collection_steps", 0)
    if exited is None:
        status = "running" if child else "not_started"
    elif exited["exit_code"] < 0 or progress.get("status") == "interrupted":
        status = "interrupted"
    elif exited["exit_code"] != 0 or progress.get("status") == "failed":
        status = "failed"
    elif collections == COLLECTION_LIMIT and progress.get("stop_reason") == "collection_iteration_limit":
        status = "completed"
    else:
        status = "interrupted"
    return {"status": status, "child_exited": exited is not None, "child": child, "child_exit": exited,
            "target_reached": status == "completed", "completed_collection_iterations": collections,
            "target_completed_collection_iterations": COLLECTION_LIMIT,
            "actual_joint_updates": progress.get("learning_phases", 0),
            "real_transitions": progress.get("real_transitions", 0),
            "training_seconds": progress.get("training_seconds")}


def actual_nodes(workspace):
    nodes = read_json(workspace / "outputs" / RUN_NAME / "nodes.json", {})
    result, seen = {}, {}
    for label in NODE_ORDER:
        if label not in nodes:
            continue
        node = nodes[label]
        if node["checkpoint"] in seen:
            result[seen[node["checkpoint"]]]["aliases"].append(label)
            continue
        seen[node["checkpoint"]] = label
        result[label] = {**node, "run_name": RUN_NAME, "label": label, "aliases": [label]}
    return result


def json_default(value):
    if callable(value):
        return f"{value.__module__}.{value.__qualname__}"
    return str(value)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=json_default) + "\n")
    tmp.replace(path)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def hardware():
    record = {"at": now(), "gpu": subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader"], text=True).strip()}
    cg = Path("/sys/fs/cgroup")
    record["cgroup_memory_current"] = (cg / "memory.current").read_text().strip()
    record["cgroup_memory"] = {k: int(v) for k, v in (line.split() for line in (cg / "memory.stat").read_text().splitlines())
                               if k in {"anon", "file", "inactive_file"}}
    return record
