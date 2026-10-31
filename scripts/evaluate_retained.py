"""Evaluate milestones plus the final checkpoint, reusing matching prior results."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    versions = {}
    for path in args.run_directory.glob("checkpoint_*.pt"):
        match = re.fullmatch(r"checkpoint_(\d+)\.pt", path.name)
        if match:
            versions[int(match.group(1))] = path
    if not versions:
        raise FileNotFoundError("No numbered checkpoints")
    selected = sorted(n for n in versions if n == 0 or n % 1000 == 0 or n == max(versions))
    for number in selected:
        checkpoint = versions[number]
        expected = args.run_directory / f"evaluation_{number:07d}.json"
        h = hashlib.sha256()
        with checkpoint.open("rb") as data:
            for chunk in iter(lambda: data.read(4 * 1024**2), b""):
                h.update(chunk)
        if expected.exists() and json.loads(expected.read_text())["checkpoint_sha256"] == h.hexdigest():
            print("EVALUATION_REUSED", number, flush=True)
            continue
        subprocess.run([sys.executable, "-u", str(ROOT / "scripts/evaluate.py"), str(checkpoint)], check=True)


if __name__ == "__main__":
    main()
