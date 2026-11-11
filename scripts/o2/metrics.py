"""CPU summaries of the saved complete, unfiltered O2 score rows."""
import csv
import json
from collections import defaultdict

from common import CODE_ROOT, QUALITY, write_csv, write_json

HARD_IDS = {r["source_clip_id"] for r in json.loads((CODE_ROOT / "configs/p10_hard_motion_set.json").read_text())["members"]}
SKILLS = ("flip", "side_roll", "cartwheel", "handstand")
INTS = {"clip_id", "source_clip_id", "reference_frames", "reference_transitions", "executed_transitions"}
BOOLS = {"completed", "hard_failure"}
STRINGS = {"name", "category", "package", "source", "termination_reason"}


def read_rows(path):
    with path.open() as stream:
        return [{k: (v if k in STRINGS else v == "True" if k in BOOLS else int(v) if k in INTS else float(v))
                 for k, v in row.items()} for row in csv.DictReader(stream)]


def aggregate(rows):
    n = len(rows)
    if not n:
        return {"clip_count": 0}
    complete = sum(r["completed"] for r in rows)
    return {"clip_count": n, "completed": complete, "failed": n - complete, "failure_rate": (n - complete) / n,
            "mean_normalized_return": sum(r["normalized_return"] for r in rows) / n,
            "mean_completion_fraction": sum(r["completion_fraction"] for r in rows) / n,
            "executed_transitions": sum(r["executed_transitions"] for r in rows),
            "reference_transitions": sum(r["reference_transitions"] for r in rows),
            "quality": {key: sum(r[key] for r in rows) / n for key in QUALITY},
            "normalized_reward_contributions": {key: sum(r[key] / r["normalization_denominator"] for r in rows) / n
                                                for key in rows[0] if key.startswith("reward_") and key != "reward_sum"}}


def groups(rows, source):
    cats = defaultdict(list)
    for row in rows:
        cats[row["category"]].append(row)
    result = {"categories": {key: aggregate(value) for key, value in sorted(cats.items())}}
    if source == "bones_full":
        result.update(fixed_hard639=aggregate([r for r in rows if r["source_clip_id"] in HARD_IDS]),
                      non_hard=aggregate([r for r in rows if r["source_clip_id"] not in HARD_IDS]),
                      skills={skill: aggregate([r for r in rows if skill in r["name"].lower()]) for skill in SKILLS})
    else:
        result.update(get_up=aggregate([r for r in rows if r["name"].startswith("fallAndGetUp")]),
                      run=aggregate([r for r in rows if r["name"].startswith("run")]))
    return result


def write_score_parts(output, rows, source):
    rows.sort(key=lambda r: r["source_clip_id"])
    parts = []
    for first in range(0, len(rows), 2000):
        name = f"per_clip_{first // 2000:04d}.csv" if source == "bones_full" else "per_clip.csv"
        write_csv(output / name, rows[first:first + 2000])
        parts.append(name)
    index = {"records": len(rows), "rows_per_part": 2000, "parts": parts,
             "order": "original_source_clip_id", "columns": list(rows[0]),
             "integer_columns": sorted(INTS), "boolean_columns": sorted(BOOLS), "string_columns": sorted(STRINGS)}
    write_json(output / "per_clip_index.json", index)
    return index


def load_scores(output):
    index = json.loads((output / "per_clip_index.json").read_text())
    return [r for p in index["parts"] for r in read_rows(output / p)]


def compare_nodes(previous, current, output):
    old = {r["source_clip_id"]: r for r in previous}
    common = [r for r in current if r["completed"] and old[r["source_clip_id"]]["completed"]]
    changed = [{"source_clip_id": r["source_clip_id"], "name": r["name"],
                "previous_complete": old[r["source_clip_id"]]["completed"], "current_complete": r["completed"]}
               for r in current if r["completed"] != old[r["source_clip_id"]]["completed"]]
    if changed:
        write_csv(output / "changed_completion.csv", changed)
    return {"new_completions": sum(r["current_complete"] for r in changed),
            "lost_completions": sum(r["previous_complete"] for r in changed),
            "common_complete": {"previous": aggregate([old[r["source_clip_id"]] for r in common]), "current": aggregate(common)},
            "all_clip_previous": aggregate(previous), "all_clip_current": aggregate(current),
            "completion_changes": "changed_completion.csv" if changed else None}
