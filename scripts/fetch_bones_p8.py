"""Acquire only official G1 and current metadata using existing HF authorization."""
import json
import os
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw/bones_seed"
RESULT = ROOT / "results/20261106-p8-stability-scale-s0/bones_data"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    for path in (Path("/root/.config/supermimic/hf_token"), ROOT / ".cache/huggingface/token", Path("/root/.cache/huggingface/token")):
        if not token and path.is_file():
            token = path.read_text().strip()
    session = requests.Session()
    if token:
        session.headers["Authorization"] = "Bearer " + token
    repo = "https://huggingface.co/datasets/bones-studio/seed"
    # Continue the same revision as the already acquired metadata/partial archive.
    prior = json.loads((RESULT / "acquisition.json").read_text()) if (RESULT / "acquisition.json").exists() else None
    if prior:
        revision = prior["revision"]
    else:
        info = session.get("https://huggingface.co/api/datasets/bones-studio/seed", timeout=60)
        info.raise_for_status()
        revision = info.json()["sha"]
    status = {"status": "downloading", "repository": repo, "revision": revision,
              "existing_credential_available": bool(token), "files": [], "started_unix": time.time()}
    for filename in ("metadata/seed_metadata_v004.csv", "g1.tar.gz"):
        target = OUT / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".partial")
        url = f"{repo}/resolve/{revision}/{filename}?download=true"
        if not target.exists():
            total = None
            failures = 0
            offset = partial.stat().st_size if partial.exists() else 0
            status.update(active_file=filename, resumed_from_bytes=offset, downloaded_bytes=offset)
            (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
            print("BONES_DOWNLOAD_RESUME", filename, offset, flush=True)
            while total is None or offset < total:
                # The observed long response broke after13.36GB. Request bounded
                # byte ranges and continue at bytes actually written, not bytes received.
                end = offset + 256 * 1024**2 - 1
                try:
                    with session.get(url, headers={"Range": f"bytes={offset}-{end}",
                            "Accept-Encoding": "identity"}, stream=True, timeout=(30, 60)) as response:
                        if response.status_code in (401, 403):
                            status.update(status="blocked_hf_access", http_status=response.status_code,
                                blocked_file=filename, server_message=response.text[:2000])
                            (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
                            print("BONES_ACCESS_BLOCKED", filename, response.status_code, flush=True)
                            return
                        response.raise_for_status()
                        content_range = response.headers.get("Content-Range", "")
                        if response.status_code != 206 or not content_range.startswith(f"bytes {offset}-"):
                            raise RuntimeError(f"Cannot append a response without the requested range: status={response.status_code}, range={content_range}")
                        total = int(content_range.rsplit("/", 1)[1])
                        print("BONES_RANGE_ACCEPTED", offset, content_range, flush=True)
                        with partial.open("ab") as output:
                            for block in response.iter_content(8 * 1024**2):
                                output.write(block)
                    offset = partial.stat().st_size
                    failures = 0
                    status.update(status="downloading", downloaded_bytes=offset, total_bytes=total, updated_unix=time.time())
                    (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
                except requests.RequestException as exc:
                    offset = partial.stat().st_size if partial.exists() else 0
                    failures += 1
                    status.update(status="download_interrupted", downloaded_bytes=offset,
                        interruption_type=type(exc).__name__, consecutive_failures=failures, updated_unix=time.time())
                    (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
                    print("BONES_CONNECTION_INTERRUPTED", type(exc).__name__, offset, failures, flush=True)
                    if failures >= 4:
                        raise
                    time.sleep(5)
            partial.replace(target)
        status["files"].append({"file": filename, "bytes": target.stat().st_size, "path": str(target)})
        (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
        print("BONES_ACQUIRED", filename, target.stat().st_size, flush=True)
    status.update(status="downloaded", completed_unix=time.time())
    (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")


if __name__ == "__main__":
    main()
