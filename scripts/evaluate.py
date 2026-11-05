"""Full 40-motion physical evaluation and the exact trajectories used for scoring."""
from pathlib import Path
import argparse
import json
import sys
import time
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from supermimic.motion import MotionLibrary, checkpoint_data_definition
from supermimic.simulator import G1Simulator
from supermimic.kinematics import ForwardKinematics
from supermimic.networks import Actor, actor_root_position_error
from supermimic.task import observation, reward_and_termination
from supermimic.geometry import quat_apply, quat_inv, quat_mul, quat_to_rotvec, yaw_quat
from supermimic.checkpointing import pin_checkpoint


@torch.no_grad()
def evaluate(checkpoint_path, output_dir, record_motions=None):
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    motions = MotionLibrary(ROOT / "data/processed/lafan1_g1_50hz", "cuda")
    if checkpoint_data_definition(checkpoint) != motions.data_definition:
        raise ValueError("Evaluation data semantics differ from training")
    cfg, iteration = checkpoint["config"], checkpoint["iteration"]
    goal_frame = cfg.get("goal_frame", "reference_heading")
    started = time.monotonic()
    actor = Actor(cfg.get("actor_root_position_feedback", False)).cuda().eval()
    actor.load_state_dict(checkpoint["actor"])
    actor_updates = checkpoint["actor_updates"]
    del checkpoint
    sim = G1Simulator(40)
    fk = ForwardKinematics(sim.host_model).float().cuda()
    clip = torch.arange(40, device="cuda")
    frame = torch.zeros(40, device="cuda", dtype=torch.long)
    initial = motions.get(clip, frame)
    sim.reset(initial["qpos"], initial["qvel"])
    previous_action = torch.zeros((40, 29), device="cuda")
    obs = observation(sim.qpos, sim.qvel, previous_action, sim.q0, sim.context[:, 1:30])
    history = obs[:, None].repeat(1, 10, 1)
    active = torch.ones(40, dtype=torch.bool, device="cuda")
    failed = torch.zeros_like(active)
    reasons = ["completed"] * 40
    tracks = []
    for i in range(40):
        tracks.append({"qpos": [sim.qpos[i].cpu().numpy().copy()],
                       "qvel": [sim.qvel[i].cpu().numpy().copy()],
                       "reference_qpos": [initial["qpos"][i].cpu().numpy().copy()],
                       "reference_qvel": [initial["qvel"][i].cpu().numpy().copy()]})
    while bool(active.any()):
        position_error = actor_root_position_error(sim.qpos, motions.get(clip, frame)["qpos"],
            cfg["actor_root_position_scale_m"]) if actor.root_position_feedback else None
        action = actor(history, motions.goal(clip, frame, goal_frame=goal_frame, root_quaternion=sim.qpos[:, 3:7]), position_error)
        qpos, qvel = sim.step(action)
        reference = motions.get(clip, frame + 1)
        reward, done, metrics = reward_and_termination(fk(qpos, qvel), reference, qpos, action,
                                                     previous_action, sim.soft_lower, sim.soft_upper)
        invalid = ~(torch.isfinite(qpos).all(-1) & torch.isfinite(qvel).all(-1) & torch.isfinite(reward))
        done |= invalid
        gravity = torch.zeros((40, 3), device="cuda"); gravity[:, 2] = -1
        robot_gz = quat_apply(quat_inv(qpos[:, 3:7]), gravity)[:, 2]
        ref_gz = quat_apply(quat_inv(reference["qpos"][:, 3:7]), gravity)[:, 2]
        values = {"qpos": qpos, "qvel": qvel, "reference_qpos": reference["qpos"],
                  "reference_qvel": reference["qvel"], "action": action, "previous_action": previous_action,
                  "reward": torch.where(invalid, torch.zeros_like(reward), reward),
                  "reward_components": metrics.pop("components"), **metrics,
                  "root_xy_error_m": (qpos[:, :2]-reference["qpos"][:, :2]).norm(dim=-1),
                  "heading_error_rad": quat_to_rotvec(quat_mul(yaw_quat(qpos[:, 3:7]),
                      quat_inv(yaw_quat(reference["qpos"][:, 3:7])))).norm(dim=-1),
                  "upright": (robot_gz < -2**-0.5) & (ref_gz < -2**-0.5),
                  "joint_rmse_rad": (qpos[:, 7:]-reference["qpos"][:, 7:]).square().mean(-1).sqrt(),
                  "survived": ~done, "invalid": invalid,
                  "tracking": ~done & (metrics["root_position_error_m"] <= .3) & (metrics["root_orientation_error_rad"] <= .4)}
        arrays = {k: v.cpu().numpy().copy() for k,v in values.items()}
        for i in torch.nonzero(active).flatten().tolist():
            for key, value in arrays.items():
                tracks[i].setdefault(key, []).append(value[i])
        just_failed = active & done
        for i in torch.nonzero(just_failed).flatten().tolist():
            reasons[i] = "nonfinite" if invalid[i] else ("root_height" if metrics["root_height_error_m"][i] > .25 else "root_tilt")
        failed |= just_failed
        active &= ~(done | (frame + 1 >= motions.lengths - 1))
        frame += 1
        obs = observation(qpos, qvel, action, sim.q0, sim.context[:, 1:30])
        history = torch.cat((history[:, 1:], obs[:, None]), 1)
        previous_action = action
        ids = torch.nonzero(~active).flatten()
        if len(ids):
            sim.reset(initial["qpos"][ids], initial["qvel"][ids], ids)
    records = []
    trajectory_dir = output_dir / "trajectories"
    trajectory_dir.mkdir()
    for i, name in enumerate(motions.names):
        arrays = {k: np.stack(v) for k,v in tracks[i].items()}
        length = int(motions.lengths[i]) - 1
        steps = len(arrays["reward"])
        row = {"motion": name, "failed": bool(failed[i]), "reason": reasons[i],
               "executed_steps": steps, "full_reference_steps": length,
               "execution_seconds": steps*.02, "failure_seconds": steps*.02 if failed[i] else None,
               "completion_fraction": steps/length, "normalized_return": float(arrays["reward"].sum(dtype=np.float64))/(.1*length),
               "tracking_coverage": float(arrays["tracking"].sum())/length,
               "reward_component_sums": arrays["reward_components"].sum(0,dtype=np.float64).tolist(),
               "upright_steps": int(arrays["upright"].sum()),
               "heading_error_upright_rad": float(arrays["heading_error_rad"][arrays["upright"]].mean()) if arrays["upright"].any() else None}
        for key in ("root_position_error_m", "root_xy_error_m", "root_orientation_error_rad", "relative_body_position_error_m", "joint_rmse_rad"):
            row["mean_"+key] = float(arrays[key].mean())
        row["last_frame_root_position_error_m"] = float(arrays["root_position_error_m"][-1])
        np.savez_compressed(trajectory_dir/(name+".npz"), **arrays, motion=name, iteration=iteration,
                            goal_frame=goal_frame, dt=.02, full_reference_steps=length)
        records.append(row)
    result = {"status": "evaluated", "method": cfg["method"], "goal_frame": goal_frame,
              "actor_root_position_feedback": cfg.get("actor_root_position_feedback", False),
              "actor_root_position_scale_m": cfg.get("actor_root_position_scale_m", 0.3),
              "world_termination_loss": cfg.get("world_termination_loss", "aux_bce"),
              "iteration": iteration, "actor_updates": actor_updates, "data_definition": motions.data_definition,
              "checkpoint_file": f"checkpoint_{iteration:07d}.pt", "motions": 40,
              "failed_motions": sum(r["failed"] for r in records), "completed_motions": sum(not r["failed"] for r in records),
              "wall_seconds": time.monotonic()-started, "clips": records,
              "trajectory_directory": "trajectories", "score_and_video_share_trajectory": True,
              "protocol": {"start_frame": 0, "friction": 1., "observation_noise": False, "domain_randomization": False,
                           "failure": "reference-relative height >0.25 m OR gravity-z difference >0.8 OR nonfinite",
                           "normalization": "0.1 * full reference transitions; failed tail zero",
                           "tracking_coverage": "survived AND position<=0.3m AND SO3<=0.4rad, divided by full reference steps",
                           "upright_heading": "both robot and reference gravity-z < -cos(pi/4)",
                           "scope": "training-motion coverage, not generalization"}}
    for key in ("normalized_return", "completion_fraction", "tracking_coverage", "execution_seconds"):
        result["mean_"+key] = sum(r[key] for r in records)/40
    (output_dir/"evaluation.json").write_text(json.dumps(result,indent=2)+"\n")
    print("FULL_EVALUATION_COMPLETE", json.dumps({k:v for k,v in result.items() if k not in ("clips","protocol","data_definition")}),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("checkpoint",type=Path)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--record-motions",nargs="+")
    args=parser.parse_args()
    source=args.checkpoint.resolve(strict=True)
    output=args.output_dir or source.parent/("evaluation_"+source.stem.split("_")[-1])
    output.mkdir(parents=True,exist_ok=False)
    with pin_checkpoint(source) as stable:
        evaluate(stable,output,args.record_motions)

if __name__ == "__main__":
    main()
