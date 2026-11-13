"""O4 identities; reuse the O3 diagnostics, metrics and same-rollout evidence."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = "20261113-o4-official-bones-long-s0"
RUN_NAME = CAMPAIGN
ARMS = {"low_lr": "o4-bones-low-lr-long-s0"}
PLAN_COMMIT = "97593b997dfadbdbd3603b24eec1e933a8138105"
PARENT_CAMPAIGN = "20261112-o3-official-bones-lr-s0"
HISTORICAL_O2_CAMPAIGN = "20261111-o2-official-bones-s0"
PARENT_SCORE_NODE = "quarter/update_32000"
TASK = "SuperMimic-GenCoord-G1"
PUBLICATION_LOCK = Path("/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock")
CODE_ROOT = Path("/root/autodl-tmp/robot-repro/supermimic-o4-official-bones")
PROTOCOL_PATH = CODE_ROOT / "configs/o4_official_bones_long_run_protocol.json"
NEW_JOINT_UPDATES = 132000
CHECKPOINT_UPDATES = (16000, 32000, 64000, 96000, 132000)
NODE_ORDER = tuple(f"update_{n:05d}" for n in CHECKPOINT_UPDATES) + ("final",)
# These unchanged helpers import this campaign's common module. The official
# patched source remains separately selected by run_d57.sh's PYTHONPATH.
sys.path.append(str(CODE_ROOT / "scripts/o3"))
QUALITY = ("root_position_error_m", "root_xy_error_m", "root_z_absolute_error_m",
           "root_orientation_error_rad", "relative_body_position_error_m", "relative_body_orientation_error_rad")


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def training_state(workspace):
    campaign = workspace / 'outputs' / CAMPAIGN
    exits_path = campaign / 'training_children_exit.json'
    exits = json.loads(exits_path.read_text()) if exits_path.exists() else {}
    progress_path = workspace / 'outputs' / ARMS['low_lr'] / 'progress.json'
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    updates = progress.get('learning_phases', 0)
    exited = set(exits) == set(ARMS)
    if not exited:
        status = 'running' if (campaign / 'budget.json').exists() else 'not_started'
    elif exits['low_lr']['exit_code'] < 0 or progress.get('status') == 'interrupted':
        status = 'interrupted'
    elif exits['low_lr']['exit_code'] != 0:
        status = 'failed'
    elif updates == NEW_JOINT_UPDATES and progress.get('stop_reason') == 'new_joint_update_limit':
        status = 'completed'
    else:
        status = 'interrupted'
    return {'status': status, 'child_exited': exited, 'target_reached': status == 'completed',
            'new_joint_updates': updates, 'target_joint_updates': NEW_JOINT_UPDATES,
            'children_exit': exits}


def actual_nodes(workspace):
    result = {}
    for arm, run in ARMS.items():
        path = workspace / 'outputs' / run / 'nodes.json'
        if not path.exists():
            continue
        nodes = json.loads(path.read_text())
        seen = {}
        for label in NODE_ORDER:
            if label not in nodes:
                continue
            node = nodes[label]
            if node['checkpoint'] in seen:
                result[seen[node['checkpoint']]]['aliases'].append(label)
                continue
            key = arm + '/' + label
            seen[node['checkpoint']] = key
            result[key] = {**node, 'arm': arm, 'run_name': run, 'label': label, 'aliases': [label]}
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
