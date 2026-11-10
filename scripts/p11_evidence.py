"""P11's seven fixed recorded-input predictions, once per prescribed model."""
import argparse
import fcntl
import statistics
import sys
import time
from pathlib import Path
import numpy as np
from p11_results import ROOT, PROTOCOL, read, write

sys.path.insert(0, str(ROOT))
import torch
from supermimic.networks import WorldModel, state_prediction_squared_coordinates
from supermimic.motion import MotionLibrary
from supermimic.robot import load_model
from supermimic.kinematics import ForwardKinematics
from supermimic.geometry import quat_mul, quat_inv, quat_to_rotvec
from supermimic.task import reward_and_termination
from position_feedback_metrics import COMPONENTS


def compute_windows(label, checkpoint_path):
    """Caller owns the existing publication lock. Reuse completed evidence."""
    p = read(PROTOCOL)
    output = ROOT/"results"/p["campaign"]/"evidence"/label
    if (output/"manifest.json").exists():
        return read(output/"manifest.json")
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    spec = read(ROOT/p["fixed_real_windows"]["manifest"])
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    model = load_model()
    fk = ForwardKinematics(model).float().cuda()
    limits = model.jnt_range[1:]
    middle, half = limits.mean(-1), (limits[:,1]-limits[:,0])*.9/2
    lower = torch.tensor(middle-half, dtype=torch.float32, device="cuda")
    upper = torch.tensor(middle+half, dtype=torch.float32, device="cuda")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    cfg = checkpoint["config"]
    mode = cfg.get("world_root_height_mode", "residual")
    iteration = checkpoint["iteration"]
    world = WorldModel(mode).cuda().eval()
    world.load_state_dict(checkpoint["world_model"])
    del checkpoint
    motions = MotionLibrary(Path(cfg["evaluation_sources"]["bones"]), "cuda", "cpu_memmap")
    summaries = []
    with torch.no_grad():
        for target in spec["windows"]:
            name = target["motion"]
            first, last = target["fixed_start_state_frame"], target["fixed_end_state_frame"]
            steps = target["prediction_steps"]
            source = ROOT/target["source"]
            with np.load(source) as z:
                offset = int(np.nonzero(z["integer_state_frames"] == first)[0][0])
                actions = torch.tensor(z["action"][offset:offset+steps], device="cuda")
                previous = torch.cat((torch.tensor(z["previous_action"][offset:offset+steps], device="cuda"), actions[-1:]))
                actual = torch.cat((torch.tensor(z["qpos"][offset:offset+steps+1], device="cuda"),
                    torch.tensor(z["qvel"][offset:offset+steps+1], device="cuda"), previous), -1)
                context = torch.tensor(z["context"], device="cuda")[None]
                clip = torch.tensor([target["source_clip_id"]], device="cuda")
                state = actual[:1]
                predictions = [state]
                rewards, components, analytic, learned = [], [], [], []
                for step in range(steps):
                    action = actions[step:step+1]
                    predicted = world(state, action, context)
                    reference = motions.get(clip, torch.tensor([first+step+1], device="cuda"))
                    reward, _, metrics = reward_and_termination(fk(predicted[:,:36], predicted[:,36:71]), reference,
                        predicted[:,:36], action, state[:,71:], lower, upper)
                    rewards.append(reward)
                    components.append(metrics["components"])
                    analytic.append(world.termination_probability(predicted, reference["qpos"], "analytic_smooth", .05))
                    learned.append(world.termination_logits(predicted, reference["qpos"]).sigmoid())
                    predictions.append(predicted)
                    state = predicted
                predicted = torch.cat(predictions)
                analytic_probability, learned_probability = torch.cat(analytic), torch.cat(learned)
                reward_prediction = torch.cat(rewards)
                actual_reward = torch.tensor(z["reward"][offset:offset+steps], device="cuda")
                errors = {
                    "z_error_m": predicted[1:,2]-actual[1:,2],
                    "vz_error_m_per_s": predicted[1:,38]-actual[1:,38],
                    "root_position_error_m": (predicted[1:,:3]-actual[1:,:3]).norm(dim=-1),
                    "root_SO3_error_rad": quat_to_rotvec(quat_mul(predicted[1:,3:7], quat_inv(actual[1:,3:7]))).norm(dim=-1),
                    "joint_rmse_rad": (predicted[1:,7:36]-actual[1:,7:36]).square().mean(-1).sqrt(),
                    "normalized_state_squared_coordinates": state_prediction_squared_coordinates(predicted[1:], actual[1:]),
                    "reward_error": reward_prediction-actual_reward}
                pred_r = predicted[1:,2]-predicted[:-1,2]-.01*(predicted[:-1,38]+predicted[1:,38])
                actual_r = actual[1:,2]-actual[:-1,2]-.01*(actual[:-1,38]+actual[1:,38])
                survival = torch.cat((torch.ones(1,device="cuda"), (1-analytic_probability).cumprod(0)))
                arrays = {"predicted_state":predicted, "actual_state":actual, "action":actions, "context":context[0],
                    "predicted_root_z":predicted[:,2], "actual_root_z":actual[:,2],
                    "predicted_root_vz":predicted[:,38], "actual_root_vz":actual[:,38],
                    "predicted_height_velocity_residual_m":pred_r, "actual_height_velocity_residual_m":actual_r,
                    "predicted_reward":reward_prediction, "predicted_reward_components":torch.cat(components),
                    "predicted_analytic_smooth_probability":analytic_probability,
                    "predicted_analytic_survival":survival, "predicted_pre_reward_survival":survival[:-1],
                    "predicted_learned_BCE_probability":learned_probability, **errors}
                path = output/(name+".npz")
                true_termination = ~z["survived"][offset:offset+steps]
                np.savez_compressed(path, **{k:v.cpu().numpy() for k,v in arrays.items()},
                    reference_qpos=z["reference_qpos"][offset:offset+steps+1],
                    reference_qvel=z["reference_qvel"][offset:offset+steps+1],
                    actual_reward=z["reward"][offset:offset+steps],
                    actual_reward_components=z["reward_components"][offset:offset+steps],
                    actual_termination=true_termination,
                    previous_action=z["previous_action"][offset:offset+steps],
                    integer_state_frames=np.arange(first,last+1), integer_action_frames=np.arange(first,last),
                    true_failure_state_frames=np.arange(first+1,last+1)[true_termination],
                    dt=.02, iteration=iteration, world_root_height_mode=mode)
                step_values = {}
                for t in (1,4,8,16,32):
                    step_values[str(t)] = {key:float(value[t-1]) for key,value in errors.items()
                        if key != "normalized_state_squared_coordinates"}
                    step_values[str(t)].update(predicted_z=float(predicted[t,2]), actual_z=float(actual[t,2]),
                        predicted_vz=float(predicted[t,38]), actual_vz=float(actual[t,38]),
                        predicted_residual_m=float(pred_r[t-1]), actual_residual_m=float(actual_r[t-1]),
                        analytic_smooth_probability=float(analytic_probability[t-1]),
                        learned_BCE_probability=float(learned_probability[t-1]),
                        pre_reward_survival=float(survival[t-1]))
                summary = {"motion":name, "source_clip_id":target["source_clip_id"], "steps":steps,
                    "source_checkpoint":str(checkpoint_path), "actual_iteration":iteration, "world_root_height_mode":mode,
                    "source_window":str(source), "state_frames_inclusive":[first,last], "action_frames_inclusive":[first,last-1],
                    "output":str(path.relative_to(ROOT)), "step_errors":step_values,
                    "true_failure_state_frames":np.arange(first+1,last+1)[true_termination].tolist(),
                    "mean": {"z_mae_m":float(errors["z_error_m"].abs().mean()),
                        "vz_mae_m_per_s":float(errors["vz_error_m_per_s"].abs().mean()),
                        "root_SO3_mean_rad":float(errors["root_SO3_error_rad"].mean()),
                        "joint_rmse_mean_rad":float(errors["joint_rmse_rad"].mean()),
                        "reward_mae":float(errors["reward_error"].abs().mean()),
                        "predicted_abs_residual_m":float(pred_r.abs().mean()),
                        "actual_abs_residual_m":float(actual_r.abs().mean())},
                    "reward_component_order":COMPONENTS,
                    "interpretation":"One recursive WM rollout from the stored true initial state and actual actions/context. Fixed failed sample, not population estimate. Analytic termination differs from learned BCE; candidate residual is constructed, not accuracy."}
                write(path.with_suffix(".json"), summary)
                summaries.append(summary)
                print("P11_FIXED_WM_WINDOW_COMPLETE",label,name,steps,flush=True)
    result = {"status":"computed", "label":label, "checkpoint":str(checkpoint_path), "actual_iteration":iteration,
        "world_root_height_mode":mode, "windows":summaries, "new_physics_rollouts":0, "recursive_WM_windows":7,
        "prediction_steps":224, "wall_seconds":time.monotonic()-started,
        "mean_over_fixed_windows":{key:statistics.mean(row["mean"][key] for row in summaries) for key in summaries[0]["mean"]}}
    write(output/"manifest.json", result)
    models = {key:read(output.parent/key/"manifest.json") for key in ("parent_hard27000", *p["jobs"])
        if (output.parent/key/"manifest.json").exists()}
    write(output.parent/"manifest.json", {"status":"all_three_computed" if len(models)==3 else "parent_computed",
        "models":models, "recursive_WM_windows":7*len(models), "prediction_steps":224*len(models),
        "planned_total_windows":21, "planned_total_prediction_steps":672, "new_physics_rollouts":0,
        "source_manifest":p["fixed_real_windows"]["manifest"]})
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("label", choices=("parent_hard27000","full8k_residual_control","full8k_velocity_height"))
    parser.add_argument("--checkpoint",type=Path)
    args=parser.parse_args()
    p=read(PROTOCOL)
    checkpoint=args.checkpoint or Path(p["parent"]["checkpoint"])
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        compute_windows(args.label,checkpoint)


if __name__ == "__main__":
    main()
