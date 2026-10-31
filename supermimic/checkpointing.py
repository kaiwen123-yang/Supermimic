"""Atomic per-iteration snapshots, bounded local history and pinned evaluations."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import time
import uuid

import torch


def save_checkpoint(payload, directory, keep_recent=20, milestone_every=1000):
    directory = Path(directory).resolve()
    iteration = int(payload["iteration"])
    target = directory / f"checkpoint_{iteration:07d}.pt"
    started = time.monotonic()
    with (directory / ".checkpoint.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.exists():
            raise FileExistsError(f"Numbered checkpoints are immutable: {target}")
        temporary = directory / "checkpoint.tmp"
        with temporary.open("wb") as output:
            torch.save(payload, output)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(target)
        alias = directory / "checkpoint-link.tmp"
        if alias.exists() or alias.is_symlink():
            alias.unlink()
        alias.symlink_to(target.name)
        alias.replace(directory / "checkpoint_latest.pt")
        versions = []
        for path in directory.glob("checkpoint_*.pt"):
            match = re.fullmatch(r"checkpoint_(\d+)\.pt", path.name)
            if match and not path.is_symlink():
                versions.append((int(match.group(1)), path))
        versions.sort()
        keep = {number for number, _ in versions[-keep_recent:]} | {0, iteration}
        for number, path in versions:
            milestone = milestone_every > 0 and number % milestone_every == 0
            if number not in keep and not milestone:
                # Only this run's numbered snapshots are pruned; milestone files
                # and the immutable hardlinks of active evaluations remain valid.
                path.unlink()
    return time.monotonic() - started


@contextmanager
def pin_checkpoint(path):
    path = Path(path).absolute()
    directory = path.parent
    snapshots = directory / ".evaluation-snapshots"
    snapshots.mkdir(exist_ok=True)
    with (directory / ".checkpoint.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        source = path.resolve(strict=True)
        pinned = snapshots / f"{source.stem}-{uuid.uuid4().hex}.pt"
        os.link(source, pinned)
    try:
        yield pinned
    finally:
        pinned.unlink(missing_ok=True)
