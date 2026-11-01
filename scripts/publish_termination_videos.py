"""Publish the requested fixed-checkpoint videos and their replay provenance from D57."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tarfile
import time

from publish_checkpoint import ROOT, REPO, URL, call, git, release_by_tag, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    directory = args.directory.absolute()
    videos = directory / "videos"
    manifest = json.loads((videos / "video_manifest.json").read_text())
    tag = "sm-20261101-termination-s0-videos-v1"
    # Decode every frame of each delivered movie; keep real failures in the videos.
    for item in [*manifest["videos"], manifest["overview"]]:
        path = videos / item["file"]
        if sha256(path) != item["sha256"]:
            raise ValueError("Video changed after rendering")
        subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", str(path), "-f", "null", "-"], check=True)
        print("VIDEO_DECODE_VERIFIED", path.name, flush=True)
    archive = directory / "termination-video-replay-evidence.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=6) as bundle:
        for mode in ("learned", "analytic_smooth"):
            bundle.add(directory / f"replay_{mode}", arcname=f"replay_{mode}")
            bundle.add(directory / f"{mode}-recording.log", arcname=f"{mode}-recording.log")
        bundle.add(directory / "video_review.json", arcname="video_review.json")
    notes = directory / "video-release-notes.md"
    notes.write_text("""# G1 termination comparison videos

Five motions selected before replay: walking, running with drift, dance, jumps, and failed get-up.
Left: kinematic reference. Middle: learned termination, checkpoint 2678. Right: analytic smooth termination, checkpoint 2793.

Full videos play at 1x with physical time and root/joint errors. Terminated panels freeze and remain labeled. The overview contains each video's first 12 seconds and, when applicable, last 4 seconds with labeled cuts. Rendering uses recorded physical qpos and does not advance physics.

These are new fixed-checkpoint replays: learned 0/40 and analytic 19/40 completed. Original published results remain 0/40 and 20/40. No training or hyperparameter change was performed for these videos.

Recorded trajectories, full 40-motion replay evaluations, logs, source hashes and video digests are included for review.
""", encoding="utf-8")
    existing = subprocess.run(["gh", "release", "view", tag, "--repo", REPO, "--json", "databaseId,isDraft"], text=True, capture_output=True)
    if existing.returncode == 0:
        release_id = json.loads(existing.stdout)["databaseId"]
    else:
        created = json.loads(call(["gh", "api", f"repos/{REPO}/releases", "--method", "POST",
            "-f", f"tag_name={tag}", "-f", f"target_commitish={args.source_commit}",
            "-f", "name=G1 termination comparison: videos and replay evidence", "-F", "draft=true", "-F", f"body=@{notes}"]))
        release_id = created["id"]
    paths = [*(videos / item["file"] for item in manifest["videos"]), videos / manifest["overview"]["file"],
             videos / "contact_sheet.jpg", videos / "video_manifest.json", directory / "video_review.json", archive]
    existing_assets = {a["name"]: a for a in release_by_tag(tag, release_id)["assets"]}
    for path in paths:
        old = existing_assets.get(path.name)
        if old:
            if old["digest"] != "sha256:" + sha256(path) or old["size"] != path.stat().st_size:
                raise ValueError(f"Refusing to replace existing video evidence: {path.name}")
        else:
            call(["gh", "release", "upload", tag, str(path), "--repo", REPO])
        print("ASSET_UPLOADED", path.name, flush=True)
    remote = release_by_tag(tag, release_id)
    verified = []
    for path in paths:
        asset = next(a for a in remote["assets"] if a["name"] == path.name)
        digest = sha256(path)
        if asset["digest"] != "sha256:" + digest or asset["size"] != path.stat().st_size:
            raise ValueError(f"Asset digest/size mismatch: {path.name}")
        verified.append({"name": path.name, "bytes": asset["size"], "sha256": digest, "url": asset["browser_download_url"]})
    target = ROOT / "results/20261101-termination-s0/videos"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(videos / "video_manifest.json", target / "video_manifest.json")
    shutil.copy2(directory / "video_review.json", target / "video_review.json")
    for mode in ("learned", "analytic_smooth"):
        shutil.copy2(directory / f"replay_{mode}/evaluation.json", target / f"replay_evaluation_{mode}.json")
    publication = {"release_url": f"https://github.com/{REPO}/releases/tag/{tag}", "source_commit": args.source_commit,
                   "assets": verified, "status": "assets_verified", "original_evaluations_unchanged": True}
    (target / "publication.json").write_text(json.dumps(publication, indent=2) + "\n")
    git("fetch", URL, "main")
    head = git("rev-parse", "FETCH_HEAD")
    worktree = ROOT / ".cache/publication-worktrees" / f"{tag}-{time.time_ns()}"
    git("worktree", "add", "--detach", str(worktree), head)
    relative = target.relative_to(ROOT)
    shutil.copytree(target, worktree / relative, dirs_exist_ok=True)
    index_path = worktree / "results/index.json"
    index = json.loads(index_path.read_text())
    index["campaigns"]["20261101-termination-s0"]["videos"] = str(relative / "publication.json")
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    git("add", "--", str(relative), "results/index.json", cwd=worktree)
    git("commit", "-m", "Publish termination comparison videos with separate replay evidence", cwd=worktree)
    git("push", URL, "HEAD:main", cwd=worktree)
    call(["gh", "release", "edit", tag, "--repo", REPO, "--draft=false", "--latest=false"])
    assert not release_by_tag(tag, release_id)["draft"]
    publication["status"] = "published_verified"
    publication["results_commit"] = git("rev-parse", "HEAD", cwd=worktree)
    (directory / "publication.json").write_text(json.dumps(publication, indent=2) + "\n")
    print("VIDEO_RELEASE_PUBLISHED", json.dumps(publication), flush=True)


if __name__ == "__main__":
    main()
