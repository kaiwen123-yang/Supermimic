"""Full per-clip records in fixed 2000-row parts, with directly usable summaries."""
import json
import re
from pathlib import Path
from position_feedback_metrics import COMPONENTS

SKILL_GROUPS = ("flip", "side_roll", "cartwheel", "handstand")
QUALITY_KEYS = ("normalized_return", "completion_fraction", "mean_root_xy_error_m",
    "mean_root_orientation_error_rad", "mean_relative_body_position_error_m", "mean_joint_rmse_rad")


def tail_group(name):
    name = name.lower()
    if "flip" in name:
        return "flip"
    if "side_roll" in name:
        return "side_roll"
    if re.search(r"(?:get_?up|stand_?up|ground|roll|lying|resting)", name):
        return "ground_getup_or_roll"
    return "other"


def write_parts(directory, rows, prefix="clips"):
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    for first in range(0, len(rows), 2000):
        name = f"{prefix}_{first//2000:04d}.jsonl"
        with (directory/name).open("w") as f:
            for row in rows[first:first+2000]:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n")
        names.append(name)
    index = {"records":len(rows), "chunk_clips":2000, "parts":names}
    (directory/(prefix+"_index.json")).write_text(json.dumps(index,indent=2)+"\n")
    return index


def read_score(path):
    score = json.loads(Path(path).read_text())
    if "clip_parts" in score:
        score["clips"] = [json.loads(line) for name in score["clip_parts"]["parts"]
            for line in (Path(path).parent/name).read_text().splitlines()]
    return score


def aggregate(rows):
    n = len(rows)
    if not n:
        return {"motions":0}
    means = {key:sum(r[key] for r in rows)/n for key in QUALITY_KEYS}
    contributions = {name:sum(r["reward_component_sums"][i]/(.1*r["full_reference_steps"]) for r in rows)/n
        for i,name in enumerate(COMPONENTS)}
    return {"motions":n, "completed_motions":sum(not r["failed"] for r in rows),
        "failed_motions":sum(r["failed"] for r in rows), "means":means,
        "reward_components_normalized":contributions,
        "missing_tail_gap":1-means["completion_fraction"],
        "executed_quality_gap":means["completion_fraction"]-means["normalized_return"]}


def groups(rows, monitor_names):
    categories = sorted({r["category"] for r in rows})
    return {"all_clips":aggregate(rows),
        "categories":{c:aggregate([r for r in rows if r["category"]==c]) for c in categories},
        "fixed_name_skill_groups":{g:aggregate([r for r in rows if g in r["motion"].lower()]) for g in SKILL_GROUPS},
        "monitor40":aggregate([r for r in rows if r["motion"] in monitor_names])}


def compact_comparison(parent, score, output):
    result = {k:score[k] for k in ("iteration","motions","completed_motions","mean_normalized_return","mean_completion_fraction")}
    result["quality"] = score["quality"]
    if parent is not None:
        old = {r["motion"]:r for r in parent["clips"]}
        identity = [{"motion":r["motion"], "parent_complete":not old[r["motion"]]["failed"],
            "current_complete":not r["failed"], "return_change":r["normalized_return"]-old[r["motion"]]["normalized_return"]} for r in score["clips"]]
        result["parent_success_denominator"] = sum(r["parent_complete"] for r in identity)
        result["parent_success_retained_count"] = sum(r["parent_complete"] and r["current_complete"] for r in identity)
        result["lost_count"] = sum(r["parent_complete"] and not r["current_complete"] for r in identity)
        result["newly_completed_count"] = sum(not r["parent_complete"] and r["current_complete"] for r in identity)
        result["identity_parts"] = write_parts(output, identity, "identity")
        common = [r for r in score["clips"] if not r["failed"] and not old[r["motion"]]["failed"]]
        result["common_complete_quality"] = {"parent":aggregate([old[r["motion"]] for r in common]), "current":aggregate(common), "conditional_only":True}
        result["parent_quality"] = parent["quality"]
    return result
