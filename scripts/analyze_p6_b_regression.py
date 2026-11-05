"""Read-only B25000/B26000 score, saved-trajectory and training-log analysis."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import statistics
import numpy as np
from analyze_p5_trajectories import window, state_event
from position_feedback_metrics import COMPONENTS

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = "20261105-p6-position-feedback-s0"
RUN = ROOT / "outputs/runs" / (CAMPAIGN + "-root_position_feedback")


def read(path):
    return json.loads(path.read_text())


def main():
    scores = {i: read(RUN / f"evaluation_{i:07d}/evaluation.json") for i in (25000, 26000)}
    old, new = ({r["motion"]: r for r in scores[i]["clips"]} for i in (25000, 26000))
    rows = []
    for name, b in new.items():
        a = old[name]
        n = min(a["executed_steps"], b["executed_steps"])
        denominator = 0.1 * a["full_reference_steps"]
        prefix, tail, comp = {}, {}, {}
        prefix_errors = {}
        for i in (25000, 26000):
            with np.load(RUN / f"evaluation_{i:07d}/trajectories/{name}.npz") as z:
                rewards = z["reward"]
                prefix[i] = float(rewards[:n].sum(dtype=np.float64)) / denominator
                tail[i] = float(rewards[n:].sum(dtype=np.float64)) / denominator
                comp[i] = z["reward_components"][:n].sum(axis=0, dtype=np.float64) / denominator
                prefix_errors[i] = {key: float(z[key][:n].mean()) for key in (
                    "root_xy_error_m", "root_orientation_error_rad", "relative_body_position_error_m")}
        rows.append({"motion": name, "score25000": a, "score26000": b,
            "return_drop": a["normalized_return"] - b["normalized_return"],
            "contribution_to_all40_drop": (a["normalized_return"] - b["normalized_return"]) / 40,
            "common_prefix_seconds": n * .02,
            "same_prefix_return_drop": prefix[25000] - prefix[26000],
            "unequal_tail_return_drop": tail[25000] - tail[26000],
            "prefix_component_contribution_drop": dict(zip(COMPONENTS, (comp[25000] - comp[26000]).tolist())),
            "prefix_error_means": prefix_errors})
    rows.sort(key=lambda r: r["return_drop"], reverse=True)
    total_drop = scores[25000]["mean_normalized_return"] - scores[26000]["mean_normalized_return"]
    mean = lambda key: statistics.mean(row[key] for row in rows)
    accounting = {"return_drop": total_drop,
        "completion_drop": scores[25000]["mean_completion_fraction"] - scores[26000]["mean_completion_fraction"],
        "common_prefix_drop": mean("same_prefix_return_drop"), "unequal_tail_drop": mean("unequal_tail_return_drop"),
        "unequal_tail_share": mean("unequal_tail_return_drop") / total_drop,
        "common_prefix_share": mean("same_prefix_return_drop") / total_drop,
        "prefix_component_drop": {k: statistics.mean(row["prefix_component_contribution_drop"][k] for row in rows) for k in COMPONENTS},
        "identity_residual": total_drop - mean("same_prefix_return_drop") - mean("unequal_tail_return_drop"),
        "motions_with_lower_return": sum(row["return_drop"] > 0 for row in rows),
        "top5_share": sum(row["contribution_to_all40_drop"] for row in rows[:5]) / total_drop,
        "top6_share": sum(row["contribution_to_all40_drop"] for row in rows[:6]) / total_drop,
        "lost_successes": [n for n in new if not old[n]["failed"] and new[n]["failed"]],
        "gained_successes": [n for n in new if old[n]["failed"] and not new[n]["failed"]],
        "interpretation": "Same-prefix comparison uses min(executed_steps) for each motion and the unchanged full-reference denominator. Unequal tails are observed rewards, not hypothetical maximum rewards or a causal intervention."}
    accounting["gap_change_C_minus_R"] = total_drop - accounting["completion_drop"]
    common = [n for n in new if not old[n]["failed"] and not new[n]["failed"]]
    common_full = {"count": len(common), "names": common,
        "scope": "B25000 and B26000 both fully complete these motions; descriptive interim subset, not the planned parent/A-final/B-final XY comparison.",
        "scores": {str(i): {key: statistics.mean((old if i == 25000 else new)[n][key] for n in common)
            for key in ("normalized_return", "mean_root_xy_error_m", "mean_root_orientation_error_rad", "mean_relative_body_position_error_m")}
            for i in (25000, 26000)}}
    common_full["component_contributions"] = {str(i): {k: statistics.mean(
        (old if i == 25000 else new)[n]["reward_component_sums"][j] / (.1 * old[n]["full_reference_steps"])
        for n in common) for j, k in enumerate(COMPONENTS)} for i in (25000, 26000)}
    events = []
    for row in rows[:6]:
        name = row["motion"]
        stop = row["score26000"]["execution_seconds"]
        pair = {}
        for i in (25000, 26000):
            with np.load(RUN / f"evaluation_{i:07d}/trajectories/{name}.npz") as z:
                arrays = {k: z[k] for k in ("qpos", "qvel", "reference_qpos", "reference_qvel", "action", "previous_action", "reward_components", "dt")}
            pair[str(i)] = {"last_two_seconds": window(arrays, max(0, stop - 2), stop),
                "same_time_events": [state_event(arrays, int(round(t / .02))) for t in sorted(set((0., 1., max(0, stop-5), max(0, stop-2), max(0, stop-1), stop)))]}
        events.append({"motion": name, "B26000_failure_seconds": stop, "B26000_reason": row["score26000"]["reason"], "trajectories": pair})
    training = {}
    keys = ("actor_gradient_norm_before_clip", "critic_mse", "wm_normalized_state_mse", "wm_termination_bce",
            "imagined_discounted_return", "imagined_survival_at_horizon", "sim_step_reward", "sim_step_termination_fraction")
    for arm in ("no_position_feedback", "root_position_feedback"):
        run = ROOT / "outputs/runs" / (CAMPAIGN + "-" + arm)
        metrics = [json.loads(line) for line in (run / "metrics.jsonl").read_text().splitlines(keepends=True) if line.endswith("\n")]
        metrics = [r for r in metrics if 24000 < r["iteration"] <= 26000]
        arm_stats = {}
        for first, last in ((24001,25000), (25001,26000), (25901,26000)):
            block = [r for r in metrics if first <= r["iteration"] <= last]
            stats = {key: {"mean": float(np.mean([r[key] for r in block])),
                "median": float(np.median([r[key] for r in block])), "p95": float(np.quantile([r[key] for r in block], .95)),
                "max": float(max(r[key] for r in block))} for key in keys}
            stats.update(updates=len(block), actor_gradient_ge10=sum(r["actor_gradient_norm_before_clip"] >= 10 for r in block),
                actor_gradient_ge100=sum(r["actor_gradient_norm_before_clip"] >= 100 for r in block),
                actual_lr_first_last={key: [block[0][key], block[-1][key]] for key in ("actor_learning_rate", "world_learning_rate", "critic_learning_rate")},
                family_transitions={k: sum(r["family_transitions"][k] for r in block) for k in block[0]["family_transitions"]},
                largest_actor_gradient_rows=[{key:r[key] for key in ("iteration", *keys)} for r in sorted(block, key=lambda r:r["actor_gradient_norm_before_clip"], reverse=True)[:5]])
            arm_stats[f"{first}-{last}"] = stats
        arm_stats["hundred_update_blocks"] = [{"first": end-99,"last":end,
            **{key: statistics.mean(r[key] for r in metrics if end-100 < r["iteration"] <= end) for key in keys},
            "actor_gradient_ge10": sum(r["actor_gradient_norm_before_clip"] >= 10 for r in metrics if end-100 < r["iteration"] <= end)}
            for end in range(24100,26001,100)]
        arm_stats["selected_update_windows"] = [{key: r[key] for key in ("iteration", *keys)}
            for r in metrics if 25297 <= r["iteration"] <= 25299 or 25985 <= r["iteration"] <= 26000]
        training[arm] = arm_stats
    result = {"created_beijing": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "source_run": str(RUN), "source_iterations": [25000,26000],
        "score_protocols": {str(i): scores[i]["protocol"] for i in scores},
        "scores": {str(i): {key:scores[i][key] for key in ("iteration","completed_motions","mean_normalized_return","mean_completion_fraction","actor_root_position_feedback")} for i in scores},
        "accounting": accounting, "ranked_motion_changes": rows, "common_full_success": common_full,
        "same_reference_time_failure_events": events, "training_logs": training,
        "scope": "Only existing scoring JSON, saved NPZ and already-written training rows. One CPU process. No checkpoint loading, inference, simulation, tests, training changes or environment changes.",
        "limits": "Accounting and paired recorded outcomes identify where return was lost, not a unique optimizer/WM causal mechanism. Training WM errors use each arm's own evolving replay; no same-action model prediction evidence is added."}
    destination = ROOT / "results" / CAMPAIGN / "b25000_to_b26000_analysis.json"
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"accounting": accounting, "common_full_success": common_full, "output":str(destination)},ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
