"""Exactly the six frozen P9 full9000 stored-action WM predictions; no physics."""
import fcntl
import sys
from pathlib import Path
import numpy as np
from p10_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results
sys.path.insert(0,str(ROOT))
import torch
from supermimic.networks import WorldModel, state_prediction_squared_coordinates
from supermimic.motion import MotionLibrary
from supermimic.robot import load_model
from supermimic.kinematics import ForwardKinematics
from supermimic.geometry import quat_mul, quat_inv, quat_to_rotvec
from supermimic.task import reward_and_termination
from position_feedback_metrics import COMPONENTS


def main():
    p=read(PROTOCOL)
    spec=p["evidence"]["WM_same_action_windows"]
    output=ROOT/"results"/p["campaign"]/"evidence"
    output.mkdir(parents=True,exist_ok=True)
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        torch.set_num_threads(2)
        torch.set_float32_matmul_precision("high")
        model=load_model()
        fk=ForwardKinematics(model).float().cuda()
        limits=model.jnt_range[1:]
        middle,half=limits.mean(-1),(limits[:,1]-limits[:,0])*.9/2
        lower=torch.tensor(middle-half,dtype=torch.float32,device="cuda")
        upper=torch.tensor(middle+half,dtype=torch.float32,device="cuda")
        checkpoint=torch.load(spec["checkpoint"],map_location="cpu",weights_only=False)
        world=WorldModel().cuda().eval()
        world.load_state_dict(checkpoint["world_model"])
        del checkpoint
        motions=MotionLibrary(Path(p["data"]["bones_evaluation_directory"]),"cuda","cpu_memmap")
        summaries=[]
        with torch.no_grad():
            for target in spec["windows"]:
                name=target["motion"]
                first=target["start_reference_state_frame"]
                last=target["end_reference_state_frame"]
                steps=target["steps"]
                source=ROOT/target["source_npz"]
                with np.load(source) as z:
                    offset=int(np.nonzero(z["integer_state_frames"]==first)[0][0])
                    actions=torch.tensor(z["action"][offset:offset+steps],device="cuda")
                    previous=torch.cat((torch.tensor(z["previous_action"][offset:offset+steps],device="cuda"),actions[-1:]))
                    actual=torch.cat((torch.tensor(z["qpos"][offset:offset+steps+1],device="cuda"),
                        torch.tensor(z["qvel"][offset:offset+steps+1],device="cuda"),previous),-1)
                    context=torch.tensor(z["context"],device="cuda")[None]
                    clip=torch.tensor([motions.names.index(name)],device="cuda")
                    state=actual[:1]
                    predictions=[state]
                    rewards,components,analytic,learned=[],[],[],[]
                    for step in range(steps):
                        action=actions[step:step+1]
                        predicted=world(state,action,context)
                        reference=motions.get(clip,torch.tensor([first+step+1],device="cuda"))
                        reward,_,metrics=reward_and_termination(fk(predicted[:,:36],predicted[:,36:71]),reference,
                            predicted[:,:36],action,state[:,71:],lower,upper)
                        rewards.append(reward)
                        components.append(metrics["components"])
                        analytic.append(world.termination_probability(predicted,reference["qpos"],"analytic_smooth",.05))
                        learned.append(world.termination_logits(predicted,reference["qpos"]).sigmoid())
                        predictions.append(predicted)
                        state=predicted
                    predicted=torch.cat(predictions)
                    analytic_probability=torch.cat(analytic)
                    errors={"root_position_error_m":(predicted[1:,:3]-actual[1:,:3]).norm(dim=-1),
                        "root_SO3_error_rad":quat_to_rotvec(quat_mul(predicted[1:,3:7],quat_inv(actual[1:,3:7]))).norm(dim=-1),
                        "joint_rmse_rad":(predicted[1:,7:36]-actual[1:,7:36]).square().mean(-1).sqrt(),
                        "normalized_state_squared_coordinates":state_prediction_squared_coordinates(predicted[1:],actual[1:])}
                    arrays={"predicted_state":predicted,"actual_state":actual,"action":actions,"context":context[0],
                        "predicted_root_z":predicted[:,2],"actual_root_z":actual[:,2],
                        "predicted_root_vz":predicted[:,38],"actual_root_vz":actual[:,38],
                        "predicted_reward":torch.cat(rewards),"predicted_reward_components":torch.cat(components),
                        "predicted_analytic_smooth_probability":analytic_probability,
                        "predicted_analytic_survival":torch.cat((torch.ones(1,device="cuda"),(1-analytic_probability).cumprod(0))),
                        "predicted_learned_BCE_probability":torch.cat(learned),**errors}
                    path=output/(name+".npz")
                    np.savez_compressed(path,**{k:v.cpu().numpy() for k,v in arrays.items()},
                        reference_qpos=z["reference_qpos"][offset:offset+steps+1],reference_qvel=z["reference_qvel"][offset:offset+steps+1],
                        actual_reward=z["reward"][offset:offset+steps],actual_reward_components=z["reward_components"][offset:offset+steps],
                        actual_termination=~z["survived"][offset:offset+steps],previous_action=z["previous_action"][offset:offset+steps],
                        integer_state_frames=np.arange(first,last+1),integer_action_frames=np.arange(first,last),dt=.02)
                    summary={"motion":name,"steps":steps,"source_checkpoint":spec["checkpoint"],"source_window":str(source),
                        "state_frames_inclusive":[first,last],"output":str(path.relative_to(ROOT)),
                        "terminal":{"predicted_z":float(predicted[-1,2]),"actual_z":float(actual[-1,2]),
                            "predicted_vz":float(predicted[-1,38]),"actual_vz":float(actual[-1,38]),
                            "root_SO3_error_rad":float(errors["root_SO3_error_rad"][-1]),
                            "joint_rmse_rad":float(errors["joint_rmse_rad"][-1]),
                            "analytic_smooth_probability":float(analytic_probability[-1]),
                            "learned_BCE_probability":float(torch.cat(learned)[-1])},
                        "reward_component_order":COMPONENTS,
                        "interpretation":"One recursive WM rollout from the stored true first state using actual recorded actions/context. No physics or Actor rollout; analytic and learned BCE probabilities are distinct."}
                    write(path.with_suffix(".json"),summary)
                    summaries.append(summary)
                    print("P10_WM_WINDOW_COMPLETE",name,steps,flush=True)
        write(output/"manifest.json",{"status":"computed","windows":summaries,"new_physics_rollouts":0,"recursive_WM_windows":6})
        state=refresh()
        commit=push_results("p10-six-prescribed-WM-windows",[(ROOT/"results"/p["campaign"]).relative_to(ROOT)],lambda idx:index_update(idx,state))
        write(output/"manifest.json",{"status":"published","windows":summaries,"new_physics_rollouts":0,"recursive_WM_windows":6,"results_commit":commit})
        state=refresh()
        push_results("p10-six-WM-windows-published",[(ROOT/"results"/p["campaign"]).relative_to(ROOT)],lambda idx:index_update(idx,state))


if __name__ == "__main__":
    main()
