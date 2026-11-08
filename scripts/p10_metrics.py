"""P10 complete clip scalars in 1000-row CSV parts and fixed-group comparisons."""
import csv
import json
from pathlib import Path
from p9_metrics import aggregate, groups as base_groups, read_score as read_legacy
from position_feedback_metrics import COMPONENTS

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "configs/p10_score_schema.json"
HARD_IDS = {r["source_clip_id"] for r in json.loads((ROOT/"configs/p10_hard_motion_set.json").read_text())["members"]}


def write_parts(directory, rows, prefix="clips"):
    directory.mkdir(parents=True, exist_ok=True)
    flat = []
    for row in rows:
        values = {k:v for k,v in row.items() if k != "reward_component_sums"}
        if "reward_component_sums" in row:
            values.update({"reward_sum_"+k:v for k,v in zip(COMPONENTS,row["reward_component_sums"])})
        flat.append(values)
    names = []
    columns = list(flat[0]) if flat else []
    for first in range(0,len(flat),1000):
        name = f"{prefix}_{first//1000:04d}.csv"
        with (directory/name).open("w",newline="") as f:
            writer = csv.DictWriter(f,fieldnames=columns)
            writer.writeheader()
            writer.writerows(flat[first:first+1000])
        names.append(name)
    index = {"records":len(rows), "chunk_clips":1000, "format":"csv", "schema":SCHEMA_PATH, "parts":names}
    (directory/(prefix+"_index.json")).write_text(json.dumps(index,indent=2)+"\n")
    return index


def read_score(path):
    path = Path(path)
    score = json.loads(path.read_text())
    if score.get("clip_parts",{}).get("format") != "csv":
        return read_legacy(path)
    schema = json.loads((ROOT/SCHEMA_PATH).read_text())
    rows = []
    for part in score["clip_parts"]["parts"]:
        with (path.parent/part).open(newline="") as f:
            for raw in csv.DictReader(f):
                row = {}
                for key,value in raw.items():
                    kind = schema["types"].get(key,"float")
                    row[key] = None if value == "" else (value if kind == "string" else
                        value == "True" if kind == "bool" else int(value) if kind == "int" else float(value))
                row["reward_component_sums"] = [row.pop("reward_sum_"+name) for name in COMPONENTS]
                rows.append(row)
    score["clips"] = rows
    return score


def groups(rows, monitor_names):
    result = base_groups(rows, monitor_names)
    result.update(fixed_hard=aggregate([r for r in rows if r["source_clip_id"] in HARD_IDS]),
        other_bones=aggregate([r for r in rows if r["source_clip_id"] not in HARD_IDS]))
    return result


def comparison(parent, score, directory):
    old = {r["motion"]:r for r in parent["clips"]}
    common = [r for r in score["clips"] if not r["failed"] and not old[r["motion"]]["failed"]]
    changed = [{"source_clip_id":r["source_clip_id"], "motion":r["motion"],
        "parent_complete":not old[r["motion"]]["failed"], "current_complete":not r["failed"],
        "return_change":r["normalized_return"]-old[r["motion"]]["normalized_return"]}
        for r in score["clips"] if r["failed"] != old[r["motion"]]["failed"]]
    result = {k:score[k] for k in ("iteration","motions","completed_motions","mean_normalized_return","mean_completion_fraction","quality")}
    result.update(parent_success_denominator=sum(not r["failed"] for r in parent["clips"]),
        parent_success_retained_count=len(common), lost_count=sum(r["parent_complete"] for r in changed),
        newly_completed_count=sum(r["current_complete"] for r in changed),
        changed_identity_parts=write_parts(directory,changed,"changed_identity"),
        common_complete_quality={"parent":aggregate([old[r["motion"]] for r in common]), "current":aggregate(common), "conditional_only":True},
        parent_quality=parent["quality"])
    for name, membership in (("fixed_hard", True),("other_bones",False)):
        selected = [r for r in common if (r["source_clip_id"] in HARD_IDS) == membership]
        result["common_complete_quality"][name] = {"parent":aggregate([old[r["motion"]] for r in selected]),"current":aggregate(selected)}
    return result
