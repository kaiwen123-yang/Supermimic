"""Export at most four already-computed rollouts from a normal policy update."""
import json
import numpy as np
import torch


@torch.no_grad()
def save_selected_rollouts(directory, block, iteration, motions, clip, frame, context,
                           states, terminal_state, references, rewards, deaths, values,
                           targets, reward_sum, bootstrap, critic_mse,
                           pre_survivals, natural_ends, geometric_probabilities):
    horizon, batch = len(rewards), len(clip)
    target = targets.reshape(horizon, batch)
    old = torch.stack(values)
    residual = (target-old[:-1]).abs().amax(0)
    ids = residual.topk(min(4, batch)).indices
    selected_states = torch.cat((states.reshape(horizon,batch,-1)[:,ids],terminal_state[ids][None]),0)
    selected_ref = torch.cat((references.reshape(horizon,batch,-1)[:,ids],
        motions.get(clip[ids],frame[ids]+horizon)["qpos"][None]),0)
    ref_vel = motions.get(clip[ids][None].expand(horizon+1,-1),
        frame[ids][None]+torch.arange(horizon+1,device=frame.device)[:,None])["qvel"]
    death = torch.stack(deaths)[:,ids]
    survival = torch.cat((torch.ones_like(death[:1]),(1-death).cumprod(0)),0)
    w,x,y,z = selected_states[...,3:7].unbind(-1)
    arrays = {"predicted_state":selected_states, "reference_qpos":selected_ref,
        "reference_qvel":ref_vel, "action":selected_states[1:,:,71:100],
        "reward":torch.stack(rewards)[:,ids], "termination_probability":death,
        "current_survival_weight":torch.stack(pre_survivals)[:,ids], "terminal_survival":survival[-1],
        "natural_end":torch.stack(natural_ends)[:,ids],
        "geometric_termination_probability":torch.stack(geometric_probabilities)[:,ids],
        "source_id":motions.source_ids[clip[ids]],
        "old_value":old[:,ids], "lambda_target":target[:,ids], "context":context[ids],
        "clip":clip[ids], "start_frame":frame[ids], "selection_score":residual[ids],
        "discounted_survival_reward_sum":reward_sum[ids], "discounted_terminal_bootstrap":bootstrap[ids],
        "objective":reward_sum[ids]+bootstrap[ids],
        "yaw_condition_D":(2*(w*z+x*y)).square()+(1-2*(y*y+z*z)).square()}
    directory.mkdir(exist_ok=True)
    path = directory / f"interval_{block:07d}.npz"
    np.savez_compressed(path, **{k:v.cpu().numpy() for k,v in arrays.items()},
        iteration=iteration, motion=np.array([motions.names[i] for i in clip[ids].tolist()]))
    path.with_suffix(".json").write_text(json.dumps({"iteration":iteration,"block_end":block,
        "critic_mse":critic_mse,"rollout_count":len(ids),"arrays":str(path),
        "selection":"Highest normal-update critic_mse in block; top max_t abs(lambda_target-old_V).",
        "parameter_phase":"WM after normal fit; Actor before policy step; stored Critic before fitting.",
        "source_names":motions.source_names,
        "termination_semantics":"current_survival_weight is pre-transition; natural_end is boolean; geometric_termination_probability is analytic soft probability before natural-end override, without threshold.",
        "state_layout":"world root XYZ, root quaternion wxyz, 29 joints, 35 velocities, previous action; dt=.02",
        "imagination_horizon":horizon,"data_manifest":str(motions.manifest_path),
        "interpretation":"Existing imagined samples, not Actor-gradient attribution or an exact checkpoint snapshot; yaw D is descriptive."},indent=2)+"\n")
