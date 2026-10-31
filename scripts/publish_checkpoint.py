"""Evaluate and publish one immutable 1000-iteration milestone from D57."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
REPO = "kaiwen123-yang/Supermimic"
URL = f"https://github.com/{REPO}.git"


def call(args, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stderr[-4000:]}")
    return result.stdout.strip()


def git(*args, cwd=ROOT):
    command = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        command += ["-c", f"http.proxy={proxy}"]
    return call(command + list(args), cwd=cwd)


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def release_by_tag(tag):
    # GitHub's by-tag endpoint omits drafts. The authenticated release listing
    # includes them and their asset digests, which are needed before publication.
    pages = json.loads(call(["gh", "api", f"repos/{REPO}/releases?per_page=100", "--paginate", "--slurp"]))
    for page in pages:
        for release in page:
            if release["tag_name"] == tag:
                return release
    raise LookupError(f"Release not found in authenticated listing: {tag}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("iteration", type=int)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.run) or args.iteration <= 0 or args.iteration % 1000:
        raise ValueError("Publication requires a named positive 1000-iteration milestone")
    run = ROOT / "outputs/runs" / args.run
    checkpoint_path = run / f"checkpoint_{args.iteration:07d}.pt"
    tag = f"sm-{args.run}-i{args.iteration:07d}"
    publication_dir = ROOT / "outputs/publications" / tag
    publication_dir.mkdir(parents=True, exist_ok=True)
    state_path = publication_dir / "publication.json"
    if state_path.exists() and json.loads(state_path.read_text()).get("status") == "verified":
        print("ALREADY_PUBLISHED", tag, flush=True)
        return
    if state_path.exists():
        previous = json.loads(state_path.read_text())
        attempts = publication_dir / "attempts"
        attempts.mkdir(exist_ok=True)
        shutil.copy2(state_path, attempts / f"{int(previous['started_unix'])}-{previous['status']}.json")
    status = {"tag": tag, "run": args.run, "iteration": args.iteration,
              "status": "preparing", "started_unix": time.time()}
    state_path.write_text(json.dumps(status, indent=2) + "\n")
    try:
        # One repo-specific publisher at a time. Training runs independently.
        (ROOT / ".cache").mkdir(exist_ok=True)
        with (ROOT / ".cache/publication.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            import torch
            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False, mmap=True)
            if checkpoint["iteration"] != args.iteration:
                raise ValueError("Checkpoint filename/payload mismatch")
            cfg = checkpoint["config"]
            checkpoint_hash = sha256(checkpoint_path)
            metadata = {"iteration": args.iteration, "actor_updates": checkpoint["actor_updates"],
                        "dataset_manifest_sha256": checkpoint["dataset_manifest_sha256"],
                        "elapsed_seconds": checkpoint["elapsed_seconds"],
                        "sim_transitions": checkpoint["collected_steps"],
                        "checkpoint_sha256": checkpoint_hash, "checkpoint_bytes": checkpoint_path.stat().st_size,
                        "replay_saved": checkpoint.get("replay_saved", False)}
            del checkpoint
            runtimes = [run / "runtime.json", *run.glob("resume_history/*/runtime.json")]
            eligible = [(json.loads(p.read_text()), p) for p in runtimes if p.exists()]
            eligible = [(r, p) for r, p in eligible if r["started_unix"] <= checkpoint_path.stat().st_mtime]
            runtime, runtime_path = max(eligible, key=lambda x: x[0]["started_unix"])
            metadata["training_source_commit"] = runtime["git_commit"]
            metadata["runtime_source"] = str(runtime_path.relative_to(ROOT))
            evaluation_path = run / f"evaluation_{args.iteration:07d}.json"
            if not evaluation_path.exists() or json.loads(evaluation_path.read_text())["checkpoint_sha256"] != checkpoint_hash:
                with (publication_dir / "evaluation.log").open("w") as log:
                    subprocess.run([sys.executable, "-u", str(ROOT / "scripts/evaluate.py"), str(checkpoint_path)], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT, check=True)
            evaluation = json.loads(evaluation_path.read_text())
            if evaluation["checkpoint_sha256"] != checkpoint_hash or evaluation["iteration"] != args.iteration:
                raise ValueError("Evaluation did not use this immutable checkpoint")
            result_dir = ROOT / "results" / args.run / "milestones" / f"iteration_{args.iteration:07d}"
            result_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(evaluation_path, result_dir / "evaluation.json")
            if cfg["method"] == "supermimic":
                diagnostic_path = run / f"diagnostics_{args.iteration:07d}.json"
                if not diagnostic_path.exists() or json.loads(diagnostic_path.read_text())["checkpoint_sha256"] != checkpoint_hash:
                    with (publication_dir / "diagnostics.log").open("w") as log:
                        subprocess.run([sys.executable, "-u", str(ROOT / "scripts/diagnose_checkpoint.py"), str(checkpoint_path)],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                shutil.copy2(diagnostic_path, result_dir / "model_diagnostics.json")
            (result_dir / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
            (result_dir / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
            rows = []
            for line in (run / "metrics.jsonl").read_text().splitlines(keepends=True):
                if line.endswith("\n"):
                    row = json.loads(line)
                    if row["iteration"] <= args.iteration:
                        rows.append(row)
            if not rows or rows[-1]["iteration"] != args.iteration:
                raise ValueError("Metrics have not reached the saved milestone")
            (result_dir / "metrics.jsonl").write_text("".join(json.dumps(row, allow_nan=False) + "\n" for row in rows))
            metadata.update(method=cfg["method"], failed_motions=evaluation["failed_motions"], motions=evaluation["motions"],
                            mean_normalized_return=evaluation["mean_normalized_return"],
                            mean_completion_fraction=evaluation["mean_completion_fraction"],
                            release_tag=tag, release_url=f"https://github.com/{REPO}/releases/tag/{tag}",
                            qualification_pass=False)
            (result_dir / "checkpoint_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
            notes = publication_dir / "release-notes.md"
            notes.write_text(
                f"G1 / LAFAN1 checkpoint at iteration {args.iteration}.\n\n"
                f"Method: {cfg['method']}; actor updates: {metadata['actor_updates']}; "
                f"simulator transitions: {metadata['sim_transitions']}.\n\n"
                f"All 40 motions evaluated from their first frame through completion or failure. "
                f"Failed motions: {evaluation['failed_motions']}/40; normalized return: {evaluation['mean_normalized_return']:.6f}. "
                "The failed tail remains in the full-duration denominator.\n\n"
                f"Training source: `{runtime['git_commit']}`. Full configuration and source hashes are attached. "
                "This is an independent learning-reproduction milestone, not a claimed paper-level pass. "
                "Optimizer states are included; simulator and replay states are rebuilt on resume.\n", encoding="utf-8")
            existing = subprocess.run(["gh", "release", "view", tag, "--repo", REPO, "--json", "isDraft,url"], text=True, capture_output=True)
            if existing.returncode == 0:
                release = json.loads(existing.stdout)
                if not release["isDraft"]:
                    remote = release_by_tag(tag)
                    asset = next((a for a in remote["assets"] if a["name"] == checkpoint_path.name), None)
                    if not asset or asset.get("digest") != "sha256:" + checkpoint_hash:
                        raise RuntimeError("Published milestone differs; refusing to overwrite its evidence")
                    status.update(status="verified", release_url=release["url"], checkpoint_sha256=checkpoint_hash,
                                  note="Existing published checkpoint verified; no published assets overwritten")
                    state_path.write_text(json.dumps(status, indent=2) + "\n")
                    return
            else:
                call(["gh", "release", "create", tag, "--repo", REPO, "--draft", "--target", runtime["git_commit"],
                      "--title", f"{cfg['method']} / LAFAN1 / iteration {args.iteration}", "--notes-file", str(notes)])
            asset_names = ["config.json", "runtime.json", "evaluation.json", "checkpoint_manifest.json", "metrics.jsonl"]
            if (result_dir / "model_diagnostics.json").exists():
                asset_names.append("model_diagnostics.json")
            assets = [checkpoint_path, *(result_dir / name for name in asset_names)]
            existing_assets = {a["name"]: a for a in release_by_tag(tag)["assets"]}
            for path in assets:
                old = existing_assets.get(path.name)
                if old and old.get("digest") == "sha256:" + sha256(path) and old["size"] == path.stat().st_size:
                    print("ASSET_ALREADY_VERIFIED", path.name, flush=True)
                    continue
                call(["gh", "release", "upload", tag, str(path), "--repo", REPO, "--clobber"])
                print("ASSET_UPLOADED", path.name, flush=True)
            remote = release_by_tag(tag)
            verified = []
            for path in assets:
                asset = next((a for a in remote["assets"] if a["name"] == path.name), None)
                digest = sha256(path)
                if not asset or asset.get("digest") != "sha256:" + digest or asset["size"] != path.stat().st_size:
                    raise RuntimeError(f"Remote asset digest/size mismatch: {path.name}")
                verified.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest})
            publication = {**metadata, "status": "assets_verified", "assets": verified, "verified_unix": time.time()}
            (result_dir / "publication.json").write_text(json.dumps(publication, indent=2) + "\n")
            # Publish compact evidence through a detached worktree, preserving
            # the active training checkout and any unrelated working edits.
            git("fetch", URL, "main")
            remote_head = git("rev-parse", "FETCH_HEAD")
            worktree = ROOT / ".cache/publication-worktrees" / f"{tag}-{int(time.time())}"
            worktree.parent.mkdir(parents=True, exist_ok=True)
            git("worktree", "add", "--detach", str(worktree), remote_head)
            relative = result_dir.relative_to(ROOT)
            shutil.copytree(result_dir, worktree / relative, dirs_exist_ok=True)
            index_path = worktree / "results/index.json"
            index = json.loads(index_path.read_text())
            index.setdefault("publications", {})[tag] = {k: metadata[k] for k in
                ("iteration", "method", "release_url", "checkpoint_sha256", "failed_motions", "motions", "mean_normalized_return")}
            index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
            git("add", "--", str(relative), "results/index.json", cwd=worktree)
            staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=worktree).returncode
            if staged:
                git("commit", "-m", f"Record {cfg['method']} LAFAN1 milestone {args.iteration}", cwd=worktree)
            results_commit = git("rev-parse", "HEAD", cwd=worktree)
            git("push", URL, "HEAD:main", cwd=worktree)
            with notes.open("a") as text:
                text.write(f"\nCompact evidence commit: `{results_commit}`. All attached asset SHA256 digests matched GitHub.\n")
            call(["gh", "release", "edit", tag, "--repo", REPO, "--notes-file", str(notes), "--draft=false", "--latest=false"])
            published = release_by_tag(tag)
            if published["draft"]:
                raise RuntimeError("Release is still a draft")
            status.update(status="verified", release_url=published["html_url"], results_commit=results_commit,
                          checkpoint_sha256=checkpoint_hash, assets=verified, completed_unix=time.time())
            state_path.write_text(json.dumps(status, indent=2) + "\n")
            print("MILESTONE_PUBLISHED", json.dumps(status), flush=True)
    except Exception as exc:
        status.update(status="failed", error=repr(exc), traceback=traceback.format_exc(), failed_unix=time.time())
        state_path.write_text(json.dumps(status, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
