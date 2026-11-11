"""Local artifact helpers for the single O1 official run."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = "20261111-o1-official-lafan40-s0"
RUN_NAME = "o1-official-lafan40-s0"
TASK = "SuperMimic-GenCoord-G1"
PUBLICATION_LOCK = Path("/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock")


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def json_default(value):
    if callable(value):
        return f"{value.__module__}.{value.__qualname__}"
    return str(value)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=json_default) + "\n")
    temporary.replace(path)
