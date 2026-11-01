"""Compare completed termination arms using existing immutable evidence only."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TAG = "20261101-termination-s0"
BASE = ROOT / "results" / TAG


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(evaluation):
    clips = evaluation["clips"]
    durations = [c["executed_steps"] * 0.02 for c in clips]
    return {"iteration": evaluation["iteration"], "completed": len(clips) - evaluation["failed_motions"],
            "motions": len(clips), "mean_seconds": statistics.mean(durations),
            "median_seconds": statistics.median(durations),
            "mean_completion_fraction": evaluation["mean_completion_fraction"],
            "mean_normalized_return": evaluation["mean_normalized_return"],
            "termination_reasons": dict(Counter(c["reason"] for c in clips))}


def main():
    evaluations, configurations, arms = {}, {}, {}
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for mode in ("learned", "analytic_smooth"):
        directory = BASE / f"supermimic_{mode}"
        status = read(directory / "status.json")
        assert status["status"] == "budget_completed"
        number = status["iteration"]
        evaluation = read(directory / f"evaluation_{number:07d}.json")
        diagnostic = read(directory / f"diagnostics_{number:07d}.json")
        boundary = read(directory / f"termination_boundary_{number:07d}.json")
        publication_dir = ROOT / "results" / f"{TAG}-{mode}" / "milestones" / f"iteration_{number:07d}"
        publication = read(publication_dir / "publication.json")
        checkpoint_hash = evaluation["checkpoint_sha256"]
        assert all(d["checkpoint_sha256"] == checkpoint_hash for d in (diagnostic, boundary, publication))
        evidence_hashes = {}
        for asset in publication["assets"]:
            if asset["name"].endswith(".pt"):
                continue  # Weight bytes were verified on D57 and against Release metadata.
            relative = (publication_dir / asset["name"]).relative_to(ROOT).as_posix()
            blob = subprocess.check_output(["git", "show", revision + ":" + relative], cwd=ROOT)
            digest = hashlib.sha256(blob).hexdigest()
            assert digest == asset["sha256"], relative
            evidence_hashes[relative] = digest
        evaluations[mode] = evaluation
        configurations[mode] = read(directory / "config.json")
        runtime = read(directory / "runtime.json")
        assert runtime["paired_initial_weights_and_rng_verified"]
        pairs = diagnostic["first_failure_pairs"]
        arms[mode] = {
            "checkpoint_sha256": checkpoint_hash, "release_url": publication["release_url"],
            "wall_seconds": status["wall_seconds"], "actor_updates": status["actor_updates"],
            "sim_transitions": status["sim_transitions"], "final_evaluation": summarize(evaluation),
            "evaluation_history": [summarize(read(p)) for p in sorted(directory.glob("evaluation_[0-9]*.json"))],
            "horizon_32": diagnostic["horizons"][-1], "termination_boundary": boundary,
            "first_failure_probability": {"samples": len(pairs), **{
                key: statistics.mean(p[key] for p in pairs) if pairs else None
                for key in ("probability_on_real_state", "probability_on_open_model_state", "probability_on_closed_model_state")}},
            "termination_on_true_states": diagnostic["termination_head_on_true_states"],
            "other_gpu_processes_at_start": runtime["other_gpu_processes"],
            "verified_git_evidence_sha256": evidence_hashes}
    old, new = evaluations["learned"], evaluations["analytic_smooth"]
    assert old["protocol"] == new["protocol"] and old["dataset_manifest_sha256"] == new["dataset_manifest_sha256"]
    changes = {k: [configurations["learned"].get(k), configurations["analytic_smooth"].get(k)]
               for k in configurations["learned"].keys() | configurations["analytic_smooth"].keys()
               if configurations["learned"].get(k) != configurations["analytic_smooth"].get(k)}
    assert set(changes) == {"imagination_termination"}
    old_clips = {c["motion"]: c for c in old["clips"]}
    per_motion, families = [], defaultdict(list)
    for c in new["clips"]:
        previous = old_clips[c["motion"]]
        assert previous["full_reference_steps"] == c["full_reference_steps"]
        per_motion.append({"motion": c["motion"], "learned": previous, "analytic_smooth": c,
                           "execution_seconds_change": 0.02 * (c["executed_steps"] - previous["executed_steps"]),
                           "normalized_return_change": c["normalized_return"] - previous["normalized_return"]})
        family = "".join(ch for ch in c["motion"].split("_")[0] if not ch.isdigit())
        families[family].append(c)
    completed = [c for c in new["clips"] if not c["failed"]]
    report = {"campaign": TAG, "evidence_commit": revision, "config_differences": changes,
              "primary_comparison": "Final checkpoints after each fixed 3-hour budget; no best-checkpoint substitution",
              "arms": arms, "per_motion": per_motion,
              "paired_improvements": {"longer_execution": sum(p["execution_seconds_change"] > 0 for p in per_motion),
                                      "higher_return": sum(p["normalized_return_change"] > 0 for p in per_motion)},
              "analytic_completed_by_family": {k: {"completed": sum(not c["failed"] for c in v), "motions": len(v)}
                                                for k, v in families.items()},
              "analytic_completed_motion_root_error_m": {
                  "count": len(completed), "mean": statistics.mean(c["root_position_error_before_failure_m"] for c in completed),
                  "min": min(c["root_position_error_before_failure_m"] for c in completed),
                  "max": max(c["root_position_error_before_failure_m"] for c in completed)},
              "interpretation_limits": [
                  "Single seed; final iteration counts and shared GPU workloads differ despite equal wall-clock budgets",
                  "Each policy visits different states; prediction error changes do not isolate world-model weights",
                  "Pre-failure horizon samples include a first failure on the current step; survival excludes it",
                  "Analytic boundary alignment follows the fixed formula; full-motion improvement is the control evidence",
                  "Completion uses original height/tilt rules and does not imply accurate global root tracking"],
              "new_training_or_simulation": False}
    (BASE / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(BASE / "comparison.json"), "paired_improvements": report["paired_improvements"],
                      "final": {k: v["final_evaluation"] for k, v in arms.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
