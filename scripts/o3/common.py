"""Paths and small artifacts for the bounded official BONES campaign."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = "20261112-o3-official-bones-lr-s0"
RUN_NAME = CAMPAIGN
ARMS = {"control": "o3-bones-lr-control-s0", "quarter": "o3-bones-lr-quarter-s0"}
PLAN_COMMIT = "e517e5c8332559514a6d49ec571aef9df70a04e3"
PARENT_CAMPAIGN = "20261111-o2-official-bones-s0"
TASK = "SuperMimic-GenCoord-G1"
PUBLICATION_LOCK = Path("/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock")
CODE_ROOT = Path("/root/autodl-tmp/robot-repro/supermimic-o3-official-bones")
NODE_ORDER = ("update_08000", "update_16000", "update_32000", "final")
QUALITY = ("root_position_error_m", "root_xy_error_m", "root_z_absolute_error_m",
           "root_orientation_error_rad", "relative_body_position_error_m", "relative_body_orientation_error_rad")


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


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
