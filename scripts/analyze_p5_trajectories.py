"""Read the specified saved scoring trajectories on CPU; never simulate or load a model."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def orientation_difference(a, b):
    dot = np.abs(np.sum(a * b, axis=-1))
    return 2 * np.arccos(np.clip(dot, 0, 1))


def state_event(z, frame):
    q, r = z["qpos"][frame], z["reference_qpos"][frame]
    v, rv = z["qvel"][frame], z["reference_qvel"][frame]
    gz, rgz = (float(2 * (p[4]**2 + p[5]**2) - 1) for p in (q, r))
    event = {"reference_seconds": round(frame * float(z["dt"]), 4), "state_frame": frame,
        "robot_height_m": float(q[2]), "reference_height_m": float(r[2]),
        "signed_height_error_m": float(q[2]-r[2]), "robot_gravity_z": gz, "reference_gravity_z": rgz,
        "gravity_z_difference_abs": abs(gz-rgz),
        "robot_tilt_from_upright_rad": float(np.arccos(np.clip(-gz,-1,1))),
        "reference_tilt_from_upright_rad": float(np.arccos(np.clip(-rgz,-1,1))),
        "root_orientation_error_rad": float(orientation_difference(q[3:7],r[3:7])),
        "robot_root_velocity_xyz_m_s": v[:3].tolist(), "reference_root_velocity_xyz_m_s": rv[:3].tolist(),
        "robot_root_speed_m_s": float(np.linalg.norm(v[:3])),
        "reference_root_speed_m_s": float(np.linalg.norm(rv[:3])),
        "robot_root_angular_speed_rad_s": float(np.linalg.norm(v[3:6])),
        "reference_root_angular_speed_rad_s": float(np.linalg.norm(rv[3:6])),
        "root_xy_error_m": float(np.linalg.norm(q[:2]-r[:2]))}
    if frame:
        action = z["action"][frame-1]
        change = action-z["previous_action"][frame-1]
        event.update(preceding_action_index=frame-1, action_rms=float(np.sqrt(np.mean(action**2))),
            action_abs_max=float(np.max(np.abs(action))), action_change_rms=float(np.sqrt(np.mean(change**2))),
            reward_components=z["reward_components"][frame-1].tolist())
    return event


def window(z, start_seconds, stop_seconds):
    dt = float(z["dt"])
    first = max(0, round(start_seconds/dt))
    last = min(len(z["qpos"])-1, round(stop_seconds/dt))
    onset_first = max(0, first-round(2/dt))
    q, ref = z["qpos"], z["reference_qpos"]
    h = q[:,2]-ref[:,2]
    tilt = np.abs(2*(q[:,4]**2+q[:,5]**2-ref[:,4]**2-ref[:,5]**2))
    events = set([onset_first, max(0,first-round(1/dt)),first,last,
                  *np.linspace(first,last,5).round().astype(int).tolist()])
    crossings = {}
    for name, values, threshold in (("abs_height_0.20m",np.abs(h),.20), ("gravity_z_difference_0.60",tilt,.60),
                                   ("physical_height_0.25m",np.abs(h),.25), ("physical_tilt_0.8",tilt,.8)):
        where = np.flatnonzero(values[onset_first:last+1]>threshold)
        crossing = onset_first+int(where[0]) if len(where) else None
        crossings[name] = {"first_seen_seconds_in_expanded_window": crossing*dt if crossing is not None else None,
                           "already_above_at_expanded_start": bool(values[onset_first]>threshold)}
        if crossing is not None:
            events.add(crossing)
    actions = z["action"][max(0,first-1):last]
    changes = actions-z["previous_action"][max(0,first-1):last]
    j = int(np.argmax(np.sqrt(np.mean(changes**2,axis=1))))+max(0,first-1)+1
    events.add(j)
    return {"requested_window_seconds":[start_seconds,stop_seconds], "available_end_seconds":last*dt,
        "expanded_start_seconds":onset_first*dt, "crossings":crossings,
        "diagnostic_threshold_note":"0.20m/0.60 are event markers only; original physical criteria remain 0.25m/0.8.",
        "window_signed_height_range_m":[float(h[first:last+1].min()),float(h[first:last+1].max())],
        "action_rms_over_window":float(np.sqrt(np.mean(actions**2))),
        "largest_action_change_seconds":j*dt,
        "events":[state_event(z,int(i)) for i in sorted(events)]}


def analyze_target(item):
    target, root = item
    name = target["motion"]
    iterations = target.get("iterations", [target.get("failed_iteration"),target.get("successful_iteration")])
    trajectories = {i:np.load(Path(root)/f"evaluation_{i:07d}/trajectories/{name}.npz") for i in iterations}
    start,end = target["reference_time_window_seconds"]
    windows = {str(i):window(z,start,end) for i,z in trajectories.items()}
    failed, other = (trajectories[i] for i in iterations)
    dt = float(failed["dt"])
    last = min(round(end/dt),len(failed["qpos"])-1,len(other["qpos"])-1)
    first = max(0,round((start-2)/dt))
    q,oq = failed["qpos"][first:last+1],other["qpos"][first:last+1]
    angular = orientation_difference(q[:,3:7],oq[:,3:7])
    action = np.sqrt(np.mean((failed["action"][first:last]-other["action"][first:last])**2,axis=1))
    pair = []
    for frame in sorted(set([first,round(start/dt),last])):
        pair.append({"reference_seconds":frame*dt,
            "root_position_difference_m":float(np.linalg.norm(failed["qpos"][frame,:3]-other["qpos"][frame,:3])),
            "root_orientation_difference_rad":float(orientation_difference(failed["qpos"][frame,3:7],other["qpos"][frame,3:7])),
            "preceding_action_rms_difference":float(np.sqrt(np.mean((failed["action"][frame-1]-other["action"][frame-1])**2)))})
    firsts = {}
    for label,values,threshold in (("orientation_difference_gt_0.3rad",angular,.3),("action_rms_difference_gt_0.5",action,.5)):
        above = np.flatnonzero(values>threshold)
        firsts[label] = {"first_seen_seconds":(first+int(above[0]))*dt if len(above) else None,
                        "already_above_at_expanded_start":bool(values[0]>threshold),
                        "meaning":"descriptive difference between two recorded policies, not a physical success criterion or causal onset"}
    for z in trajectories.values():
        z.close()
    return {"motion":name,"iterations":iterations,"windows":windows,"same_reference_time_comparison":pair,
        "difference_markers":firsts,
        "interpretation":"Signed height, gravity-z, velocities and preceding actions describe the observed phase. Inter-policy differences can precede this local window; these records alone do not identify Actor LR as the cause."}


def final_failure_windows(evaluation_dir):
    score = json.loads((evaluation_dir/"evaluation.json").read_text())
    reports=[]
    for row in score["clips"]:
        if row["failed"]:
            with np.load(evaluation_dir/"trajectories"/(row["motion"]+".npz")) as z:
                reports.append({"motion":row["motion"],"reason":row["reason"],
                    "failure_seconds":row["failure_seconds"],"completion_fraction":row["completion_fraction"],
                    "early_or_late_description":f"Failed at {row['execution_seconds']:.2f}s of {row['full_reference_steps']*.02:.2f}s",
                    "window":window(z,max(0,row["failure_seconds"]-.64),row["failure_seconds"])})
    return {"iteration":score["iteration"],"actual_failed_motions":reports,
        "alignment":"qpos/qvel/reference include frame0; action[k] leads to state[k+1]. No new physics or model prediction.",
        "scope":"All actual failed motions in this formal evaluation."}


def main():
    protocol=json.loads((ROOT/"configs/next_stage_stability_protocol.json").read_text())
    spec=protocol["existing_trajectory_analysis"]
    with ProcessPoolExecutor(max_workers=4) as pool:
        reports=list(pool.map(analyze_target,[(t,spec["parent_run_directory"]) for t in spec["targets"]]))
    result=ROOT/"results"/protocol["campaign"]
    result.mkdir(parents=True,exist_ok=True)
    (result/"p4_trajectory_events.json").write_text(json.dumps({"source":spec["parent_run_directory"],
        "state_alignment":"State frame0 is initial; action[k], previous_action[k], reward[k] belong to transition to state[k+1].",
        "cpu_workers":4,"new_simulation":False,"targets":reports},indent=2)+"\n")
    print("P4_SAVED_TRAJECTORY_ANALYSIS_COMPLETE",len(reports),flush=True)


if __name__=="__main__":
    main()
