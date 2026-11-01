"""Download only the pinned G1 motions and robot asset onto the execution host."""
from __future__ import annotations

import fnmatch
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motions-only", action="store_true")
    args = parser.parse_args()
    cfg = json.loads((ROOT / "configs/sources.lock.json").read_text())
    ds = cfg["lafan1"]
    out = ROOT / "data/raw/lafan1_g1"
    out.mkdir(parents=True, exist_ok=True)
    api = f"https://huggingface.co/api/datasets/{ds['repo']}/revision/{ds['revision']}"
    with urllib.request.urlopen(api, timeout=60) as response:
        info = json.load(response)
    if info["sha"] != ds["revision"]:
        raise RuntimeError("Dataset revision changed")
    clips = sorted(x["rfilename"] for x in info["siblings"] if fnmatch.fnmatch(x["rfilename"], ds["pattern"]))
    if len(clips) != ds["expected_clips"]:
        raise RuntimeError(f"Expected 40 clips, found {len(clips)}")
    records = []
    previous_path = out / "download_manifest.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {"files": []}
    known = {x["path"]: x for x in previous["files"]}
    for name in clips + ["README.md", "LICENSE"]:
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        valid = path.exists() and name in known and path.stat().st_size == known[name]["bytes"]
        if not valid:
            url = f"https://huggingface.co/datasets/{ds['repo']}/resolve/{ds['revision']}/{urllib.parse.quote(name)}"
            part = path.with_suffix(path.suffix + ".part")
            start = time.monotonic()
            written = 0
            with urllib.request.urlopen(url, timeout=120) as response, part.open("wb") as target:
                while chunk := response.read(512 * 1024):
                    target.write(chunk)
                    written += len(chunk)
                    # One connection, at most 4 MiB/s; avoid competing with pi transfers.
                    delay = written / (4 * 1024**2) - (time.monotonic() - start)
                    if delay > 0:
                        time.sleep(delay)
            part.replace(path)
        row = {"path": name, "bytes": path.stat().st_size}
        records.append(row)
        previous_path.write_text(json.dumps({"repo": ds["repo"], "revision": ds["revision"], "files": records}, indent=2) + "\n")
        print(f"DATA {name} {row['bytes']} bytes", flush=True)
    if args.motions_only:
        return
    asset = cfg["mjlab_asset"]
    checkout = ROOT / "upstream/mjlab"
    if not (checkout / ".git").exists():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", asset["repo"], str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "sparse-checkout", "set", asset["path"]], check=True)
    subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", asset["revision"]], check=True)
    actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if actual != asset["revision"]:
        raise RuntimeError("Robot asset revision mismatch")
    print(f"SOURCES_COMPLETE clips={len(clips)} asset={actual}", flush=True)


if __name__ == "__main__":
    main()
