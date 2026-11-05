"""P6 reward accounting from the existing full-duration scoring records."""
import statistics


COMPONENTS = ("relative_body_position", "body_orientation", "body_linear_velocity",
              "body_angular_velocity", "global_root_position", "global_root_orientation",
              "action_difference_penalty", "soft_joint_limit_penalty")
MAX_CONTRIBUTIONS = (0.2, 0.2, 0.2, 0.2, 0.1, 0.1, 0.0, 0.0)


def reward_quality(score):
    rows = []
    for clip in score["clips"]:
        completion, returned = clip["completion_fraction"], clip["normalized_return"]
        contributions = [value / (0.1 * clip["full_reference_steps"])
                         for value in clip["reward_component_sums"]]
        rows.append({"motion": clip["motion"], "mean_return": returned,
            "completion_fraction": completion, "total_gap": 1 - returned,
            "missing_tail_gap": 1 - completion, "executed_quality_gap": completion - returned,
            "components": {name: {"normalized_contribution": value,
                "executed_available_maximum": maximum * completion,
                "executed_quality_gap": maximum * completion - value}
                for name, maximum, value in zip(COMPONENTS, MAX_CONTRIBUTIONS, contributions)}})
    means = {key: statistics.mean(row[key] for row in rows) for key in
             ("mean_return", "completion_fraction", "total_gap", "missing_tail_gap", "executed_quality_gap")}
    means["components"] = {name: {key: statistics.mean(row["components"][name][key] for row in rows)
        for key in ("normalized_contribution", "executed_available_maximum", "executed_quality_gap")}
        for name in COMPONENTS}
    return {"mean": means, "per_motion": rows,
        "scope": "Equal-weight full-reference normalization across all 40 motions, including failed tails.",
        "identity": "1-R = (1-C) + (C-R); six positive deficits plus two penalty losses give C-R."}
