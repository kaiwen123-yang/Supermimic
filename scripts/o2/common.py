"""Paths and small artifacts for the bounded official BONES campaign."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = "20261111-o2-official-bones-s0"
RUN_NAME = "o2-official-bones-s0"
TASK = "SuperMimic-GenCoord-G1"
PUBLICATION_LOCK = Path("/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock")
CODE_ROOT = Path("/root/autodl-tmp/robot-repro/supermimic-o2-official-bones")
NODE_ORDER = ("hour_03", "hour_06", "final")
QUALITY = ("root_position_error_m", "root_xy_error_m", "root_z_absolute_error_m",
           "root_orientation_error_rad", "relative_body_position_error_m", "relative_body_orientation_error_rad")


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


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
