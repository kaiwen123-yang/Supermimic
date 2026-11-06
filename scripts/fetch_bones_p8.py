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
    info = session.get("https://huggingface.co/api/datasets/bones-studio/seed", timeout=60)
    info.raise_for_status()
    revision = info.json()["sha"]
    status = {"status": "downloading", "repository": repo, "revision": revision,
              "existing_credential_available": bool(token), "files": [], "started_unix": time.time()}
    for filename in ("metadata/seed_metadata_v004.csv", "g1.tar.gz"):
        url = f"{repo}/resolve/{revision}/{filename}"
        with session.get(url, stream=True, timeout=(30, 60)) as response:
            if response.status_code in (401, 403):
                status.update(status="blocked_hf_access", http_status=response.status_code,
                    blocked_file=filename, server_message=response.text[:2000],
                    required_user_action="Log in to the authorized Hugging Face account at the dataset page, accept BONES-SEED conditions/share requested account information, and make its authorized read token available in the existing HF login.")
                (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
                print(json.dumps(status), flush=True)
                return
            response.raise_for_status()
            target = OUT / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(target.suffix + ".partial")
            with partial.open("wb") as output:
                for block in response.iter_content(8 * 1024**2):
                    output.write(block)
            partial.replace(target)
        status["files"].append({"file": filename, "bytes": target.stat().st_size, "path": str(target)})
        (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")
        print("BONES_ACQUIRED", filename, target.stat().st_size, flush=True)
    status.update(status="downloaded", completed_unix=time.time())
    (RESULT / "acquisition.json").write_text(json.dumps(status, indent=2)+"\n")


if __name__ == "__main__":
    main()
