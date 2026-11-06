"""The prescribed P6 saved-data windows and six B33000 same-action WM predictions."""
import fcntl
import json
import sys
from pathlib import Path
import numpy as np
from p7_results import ROOT, PROTOCOL, read, write, refresh_campaign, update_index
from analyze_p5_trajectories import state_event
from position_feedback_metrics import COMPONENTS

STATE_KEYS=("qpos","qvel","reference_qpos","reference_qvel")
STEP_KEYS=("action","previous_action","reward","reward_components","root_position_error_m",
    "root_orientation_error_rad","relative_body_position_error_m","root_height_error_m","tilt_error",
    "root_xy_error_m","heading_error_rad","upright","joint_rmse_rad","survived","invalid","tracking")
CONTEXT=np.array([1.]+[0.]*32,dtype=np.float32)


def export_physical_window(run, iteration, motion, first, last, output):
    source=run/f"evaluation_{iteration:07d}"/"trajectories"/(motion+".npz")
    output.mkdir(parents=True,exist_ok=True)
    path=output/f"i{iteration:07d}_{motion}_{first}_{last}.npz"
    with np.load(source) as z:
        arrays={key:z[key][first:last+1] for key in STATE_KEYS}
        arrays.update({key:z[key][first:last] for key in STEP_KEYS})
        arrays.update(integer_state_frames=np.arange(first,last+1),integer_action_frames=np.arange(first,last),
            context=CONTEXT,dt=z["dt"],motion=motion,iteration=iteration)
        np.savez_compressed(path,**arrays)
        summary={"motion":motion,"iteration":iteration,"source_trajectory":str(source),
            "source_checkpoint":str(run/f"checkpoint_{iteration:07d}.pt"),"npz":str(path.relative_to(ROOT)),
            "state_frames_inclusive":[first,last],"state_samples":last-first+1,"transition_samples":last-first,
            "time_seconds":[first*float(z["dt"]),last*float(z["dt"])],"dt":float(z["dt"]),
            "alignment":"action[k] and previous_action[k] belong to the transition state[k] -> state[k+1].",
            "coordinates":"qpos: world root XYZ, root quaternion wxyz, 29 joints; qvel: world linear, root-local angular, joint velocities.",
            "context_provenance":"[1,0x32] constructed from deterministic evaluation definition, not stored in the old NPZ.",
            "reward_component_order":list(COMPONENTS),"reward_sum":float(z["reward"][first:last].sum(dtype=np.float64)),
            "reward_component_sums":z["reward_components"][first:last].sum(0,dtype=np.float64).tolist(),
            "events":[state_event(z,int(i)) for i in np.linspace(first,last,5).round().astype(int)],
            "forces":"No measured actuator/contact force arrays; action statistics are not saturation evidence."}
    write(path.with_suffix(".json"),summary)
    return {k:summary[k] for k in ("motion","iteration","npz","source_trajectory","state_frames_inclusive")}


def saved_windows(spec, output):
    run=Path(spec["source_server_run"])
    current=[]
    for target in spec["current_failure_windows"]:
        first,last=target["state_frames_inclusive"]
        for iteration in (target["failed_iteration"],target["successful_iteration"]):
            if iteration is not None:
                current.append(export_physical_window(run,iteration,target["motion"],first,last,output/"current_failures"))
    regression=[]
    for target in spec["regression_31000"]["targets"]:
        first,last=target["state_frames_inclusive"]
        for iteration in (31000,30000):
            regression.append(export_physical_window(run,iteration,target["motion"],first,last,output/"regression_31000"))
    rows=[]
    with (run/"metrics.jsonl").open() as log:
        for line in log:
            row=json.loads(line)
            if 30001<=row["iteration"]<=31000:
                rows.append(row)
    centers={key:max(rows,key=lambda row:row[key])["iteration"] for key in ("critic_mse","actor_gradient_norm_before_clip")}
    selected=[row for row in rows if any(abs(row["iteration"]-i)<=10 for i in centers.values())]
    write(output/"regression_31000"/"local_training_events.json",{"source":str(run/"metrics.jsonl"),
        "interval":[30001,31000],"centers":centers,"rows":selected,
        "interpretation":"Two selected local sequences, overlapping rows merged. Preclip norm is not Adam displacement; no reconstruction of historical replay."})
    return current,regression,centers


def world_windows(spec, output, evaluation_iteration=33000):
    sys.path.insert(0,str(ROOT))
    import torch
    from supermimic.networks import WorldModel
    from supermimic.motion import MotionLibrary
    from supermimic.robot import load_model
    from supermimic.kinematics import ForwardKinematics
    from supermimic.geometry import quat_to_rotvec, quat_mul, quat_inv
    from supermimic.task import reward_and_termination
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    model=load_model()
    fk=ForwardKinematics(model).float().cuda()
    limits=model.jnt_range[1:]
    mid,half=limits.mean(-1),(limits[:,1]-limits[:,0])*.9/2
    lower=torch.tensor(mid-half,dtype=torch.float32,device="cuda")
    upper=torch.tensor(mid+half,dtype=torch.float32,device="cuda")
    checkpoint=torch.load(spec["model_windows"]["checkpoint"],map_location="cpu",weights_only=False)
    world=WorldModel().cuda().eval()
    world.load_state_dict(checkpoint["world_model"])
    del checkpoint
    motions=MotionLibrary(ROOT/"data/processed/lafan1_g1_50hz","cuda")
    context=torch.tensor(CONTEXT,device="cuda")[None]
    output.mkdir(parents=True,exist_ok=True)
    summaries=[]
    with torch.no_grad():
        for target in spec["current_failure_windows"]:
            name=target["motion"]
            source=Path(spec["source_server_run"])/f"evaluation_{evaluation_iteration:07d}/trajectories"/(name+".npz")
            with np.load(source) as z:
                failure_frame=target["state_frames_inclusive"][1]
                for before_steps in (64,32):
                    first=failure_frame-before_steps
                    q=torch.tensor(z["qpos"][first:first+33],device="cuda")
                    v=torch.tensor(z["qvel"][first:first+33],device="cuda")
                    previous=torch.tensor(z["action"][first-1:first+32],device="cuda")
                    actual=torch.cat((q,v,previous),-1)
                    actions=torch.tensor(z["action"][first:first+32],device="cuda")
                    state=actual[:1]
                    predicted=[state]
                    rewards,components,probabilities=[],[],[]
                    clip=torch.tensor([motions.names.index(name)],device="cuda")
                    for step in range(32):
                        action=actions[step:step+1]
                        next_state=world(state,action,context)
                        ref=motions.get(clip,torch.tensor([first+step+1],device="cuda"))
                        reward,_,metrics=reward_and_termination(fk(next_state[:,:36],next_state[:,36:71]),
                            ref,next_state[:,:36],action,state[:,71:],lower,upper)
                        rewards.append(reward)
                        components.append(metrics["components"])
                        probabilities.append(world.termination_probability(next_state,ref["qpos"],"analytic_smooth",.05))
                        predicted.append(next_state)
                        state=next_state
                    pred=torch.cat(predicted)
                    errors={"root_position_m":(pred[1:,:3]-actual[1:,:3]).norm(dim=-1),
                        "root_SO3_rad":quat_to_rotvec(quat_mul(pred[1:,3:7],quat_inv(actual[1:,3:7]))).norm(dim=-1),
                        "joint_position_rmse_rad":(pred[1:,7:36]-actual[1:,7:36]).square().mean(-1).sqrt(),
                        "root_linear_velocity_error_m_s":(pred[1:,36:39]-actual[1:,36:39]).norm(dim=-1),
                        "root_local_angular_velocity_error_rad_s":(pred[1:,39:42]-actual[1:,39:42]).norm(dim=-1),
                        "joint_velocity_rmse_rad_s":(pred[1:,42:71]-actual[1:,42:71]).square().mean(-1).sqrt()}
                    pred_reward=torch.cat(rewards).cpu().numpy()
                    pred_components=torch.cat(components).cpu().numpy()
                    pred_prob=torch.cat(probabilities).cpu().numpy()
                    actual_reward=z["reward"][first:first+32]
                    actual_components=z["reward_components"][first:first+32]
                    actual_done=~z["survived"][first:first+32]
                    path=output/f"{name}_frame{first}_h32.npz"
                    np.savez_compressed(path,predicted_state=pred.cpu().numpy(),actual_state=actual.cpu().numpy(),
                        reference_qpos=z["reference_qpos"][first:first+33],reference_qvel=z["reference_qvel"][first:first+33],
                        action=actions.cpu().numpy(),context=CONTEXT,integer_state_frames=np.arange(first,first+33),dt=.02,
                        predicted_reward=pred_reward,actual_reward=actual_reward,predicted_reward_components=pred_components,
                        actual_reward_components=actual_components,predicted_analytic_smooth_probability=pred_prob,
                        actual_termination=actual_done,**{k:t.cpu().numpy() for k,t in errors.items()})
                    summary={"motion":name,"source_checkpoint":spec["model_windows"]["checkpoint"],"source_trajectory":str(source),
                        "npz":str(path.relative_to(ROOT)),"start_frame":first,"state_frames_inclusive":[first,first+32],
                        "seconds_before_failure_at_start":before_steps*.02,"covers_terminal_step":before_steps==32,
                        "initial_previous_action_index":first-1,"action_indices":[first,first+31],
                        "horizons":{str(h):{**{k:float(t[h-1]) for k,t in errors.items()},
                            "predicted_reward_at_step":float(pred_reward[h-1]),"actual_reward_at_step":float(actual_reward[h-1]),
                            "predicted_cumulative_reward":float(pred_reward[:h].sum(dtype=np.float64)),
                            "actual_cumulative_reward":float(actual_reward[:h].sum(dtype=np.float64)),
                            "predicted_component_sums":pred_components[:h].sum(0,dtype=np.float64).tolist(),
                            "actual_component_sums":actual_components[:h].sum(0,dtype=np.float64).tolist(),
                            "predicted_analytic_smooth_probability":float(pred_prob[h-1]),"actual_termination":bool(actual_done[h-1])}
                            for h in (8,16,32)},"reward_component_order":list(COMPONENTS),
                        "context_provenance":"Constructed deterministic evaluation [1,0x32].",
                        "interpretation":"New same-recorded-action WM prediction versus saved physics, not Actor closed-loop rollout. Analytic_smooth probability is not learned BCE-head output or proof of correct Jacobians."}
                    write(path.with_suffix(".json"),summary)
                    summaries.append(summary)
    return summaries


def main():
    from publish_checkpoint import push_results
    protocol=read(PROTOCOL)
    spec=protocol["evidence_backfill"]
    output=ROOT/spec["output_root"]
    output.mkdir(parents=True,exist_ok=True)
    write(output/"manifest.json",{"status":"extracting","new_physics_rollouts":0})
    current,regression,centers=saved_windows(spec,output)
    print("P7_PHYSICAL_EVIDENCE_EXTRACTED",len(current),len(regression),centers,flush=True)
    with (ROOT/"work/p2-publication.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        predictions=world_windows(spec,output/"B33000_world_model")
        manifest={"status":"computed","current_physical_windows":current,"regression_physical_windows":regression,
            "model_windows":[{k:s[k] for k in ("motion","npz","start_frame","covers_terminal_step")} for s in predictions],
            "local_log_centers":centers,"new_physics_rollouts":0,"world_model_checkpoint":spec["model_windows"]["checkpoint"],
            "dance_success_control":None,"scope":"Only P7 prescribed saved windows/log events and six B33000 same-action predictions."}
        write(output/"manifest.json",manifest)
        lines=["# P6 指定短窗与当前世界模型证据","",
            "已提取当前失败/成功对照5窗、B31回撤/成功对照8窗，以及指定两个日志极值附近的局部序列。dance无同支成功对照。所有物理数据来自既有评分，未新增仿真。","",
            "| 动作 | 起点帧 | 覆盖终止步 | H32位置误差m | H32根SO3误差rad | H32预测终止概率 | 真实终止 |",
            "|---|---:|---|---:|---:|---:|---|"]
        for s in predictions:
            h=s["horizons"]["32"]
            lines.append(f"| {s['motion']} | {s['start_frame']} | {s['covers_terminal_step']} | {h['root_position_m']:.6f} | {h['root_SO3_rad']:.6f} | {h['predicted_analytic_smooth_probability']:.6f} | {h['actual_termination']} |")
        lines += ["","8/16/32步误差、奖励及8项贡献见各JSON；原值见配套NPZ。较早起点的H32在失败前0.64秒结束，后一个起点覆盖终止当步。",
            "","这些预测描述当前B33000在真实失败附近的状态与奖励失配，不重建B25987或B31训练时的replay，不据此改动训练。解析终止概率来自analytic_smooth；状态预测误差本身不能判定Jacobian是否准确。"]
        (output/"conclusion.md").write_text("\n".join(lines)+"\n")
        campaign=refresh_campaign(protocol)
        paths=[output.relative_to(ROOT),Path("results")/protocol["campaign"]/"summary.json"]
        commit=push_results("p7-prescribed-p6-evidence",paths,lambda index:update_index(index,campaign))
        manifest.update(status="published",results_commit=commit)
        write(output/"manifest.json",manifest)
        protocol=read(PROTOCOL)
        protocol["execution"]["evidence_backfill_done"]=True
        write(PROTOCOL,protocol)
        campaign=refresh_campaign(protocol)
        p6_summary=ROOT/"results/20261105-p6-position-feedback-s0/summary.json"
        prior=read(p6_summary)
        prior.update(followup_evidence_status="published",followup_evidence_manifest=str((output/"manifest.json").relative_to(ROOT)))
        write(p6_summary,prior)
        push_results("p7-prescribed-evidence-confirmed",paths+[PROTOCOL.relative_to(ROOT),p6_summary.relative_to(ROOT)],
                     lambda index:update_index(index,campaign))
        print("P7_PRESCRIBED_EVIDENCE_PUBLISHED",commit,flush=True)


if __name__=="__main__":
    main()
