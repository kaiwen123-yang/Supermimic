"""Close each P10 job at its actual bounded endpoint without starting another stage."""
import argparse
import fcntl
import shutil
import statistics
import time
from pathlib import Path
import numpy as np
from p10_results import ROOT, PROTOCOL, read, write, refresh, index_update, success, paired_comparisons
from p10_metrics import read_score, write_parts
from publish_p10 import publish
from publish_checkpoint import push_results
from finish_tracking_campaign import training_summary
from p7_evidence import STATE_KEYS, STEP_KEYS, CONTEXT


def finish(name):
    p = read(PROTOCOL)
    job = p["jobs"][name]
    run = ROOT/"outputs/runs"/job["run"]
    campaign = ROOT/"results"/p["campaign"]
    jobdir = campaign/"jobs"/name
    status = read(run/"status.json")
    final = status["iteration"]
    nodes = sorted({i for i in p["evaluation"]["lafan_iterations"] if i<=final}|{final})
    publications = [publish(run.name,i,i==final) for i in nodes]
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        full_nodes = sorted({i for i in p["evaluation"]["bones_iterations"] if i<=final}|{final})
        scores = {i:read_score(run/f"evaluation_{i:07d}/evaluation.json") for i in full_nodes}
        tail = [i for i in p["evaluation"]["bones_iterations"] if i in scores]
        intersection = sorted(set.intersection(*(success(scores[i]) for i in tail))) if tail else []
        score = scores[final]
        retained = read(run/f"lafan_retention_{final:07d}/evaluation.json")
        write(jobdir/"training.json",training_summary(run))
        shutil.copytree(run/f"evaluation_{final:07d}/failure_tails",jobdir/"final_failure_windows",dirs_exist_ok=True)
        windows = []
        destination = jobdir/"lafan_failure_windows"
        destination.mkdir(parents=True,exist_ok=True)
        for row in retained["clips"]:
            if row["failed"]:
                source = run/f"lafan_retention_{final:07d}/trajectories"/(row["motion"]+".npz")
                last = row["executed_steps"]
                first = max(0,last-132)
                with np.load(source) as z:
                    arrays = {k:z[k][first:last+1] for k in STATE_KEYS}
                    arrays.update({k:z[k][first:last] for k in STEP_KEYS})
                    arrays.update(integer_state_frames=np.arange(first,last+1),integer_action_frames=np.arange(first,last),
                        context=CONTEXT,dt=.02,motion=row["motion"],iteration=final)
                    np.savez_compressed(destination/(row["motion"]+".npz"),**arrays)
                windows.append({"motion":row["motion"],"source":str(source),"state_frames_inclusive":[first,last]})
        write(destination/"manifest.json",windows)
        costs = {"stage_wall_seconds":status["stage_wall_seconds"],"inherited_training_seconds":p["source"]["total_known_training_seconds"],
            "total_known_training_seconds":p["source"]["total_known_training_seconds"]+status["stage_wall_seconds"],
            "new_joint_updates":status["new_joint_updates"],"new_sim_transitions":status["new_sim_transitions"],
            "imagined_steps":status["new_actor_updates"]*8192*32,"WM_prediction_steps":status["new_training_iterations"]*10*4096*8,
            "evaluation_wall_seconds":sum(s["wall_seconds"] for s in scores.values())+sum(read(run/f"lafan_retention_{i:07d}/evaluation.json")["wall_seconds"] for i in nodes),
            "shared_gpu":True}
        comparison = {"actual_endpoint":final,"target_endpoint":27000,"full_bones_nodes":full_nodes,"lafan_nodes":nodes,
            "cost":costs,"tail":{"prescribed":[15000,21000,27000],"available":tail,
                "mean_return":statistics.mean(scores[i]["mean_normalized_return"] for i in tail) if tail else None,
                "complete_tail_available":len(tail)==3,"success_intersection_count":len(intersection),
                "success_intersection_parts":write_parts(jobdir,[{"motion":n} for n in intersection],"tail_intersection")}}
        write(jobdir/"comparison.json",comparison)
        summary = read(jobdir/"summary.json")
        summary.update(status="publishing",training_done=True,full_clip_evaluation_done=True,final_iteration=final,
            training_snapshot=status,cost=costs,evaluated_bones_iterations=full_nodes,evaluated_lafan_iterations=nodes,publications=publications)
        write(jobdir/"summary.json",summary)
        quality = score["quality"]
        lines = [f"# P10 {name} 实际结果","",f"实际终点 {final}，计划27000或累计新阶段40h；本阶段联合更新 {status['new_joint_updates']} 次，用时 {status['stage_wall_seconds']/3600:.4f}h。完整恢复P9 full9000，前序 {p['source']['total_known_training_seconds']/3600:.4f}h 单列。",
            "", "| 集合 | 完整 | 回报 | body orientation贡献 | 缺失尾段 | 执行质量缺口 |", "|---|---:|---:|---:|---:|---:|"]
        for group in ("all_clips","fixed_hard","other_bones"):
            v=quality[group]
            lines.append(f"| {group} | {v['completed_motions']}/{v['motions']} | {v['means']['normalized_return']:.8f} | {v['reward_components_normalized']['body_orientation']:.8f} | {v['missing_tail_gap']:.8f} | {v['executed_quality_gap']:.8f} |")
        lines += ["",f"LAFAN保持 {retained['completed_motions']}/40，R={retained['mean_normalized_return']:.8f}。起身/跑步及父29成功保持身份见逐节点comparison.json。",
            "", "| 名称技能 | 完整 | 回报 |", "|---|---:|---:|"]
        for group,v in quality["fixed_name_skill_groups"].items():
            lines.append(f"| {group} | {v['completed_motions']}/{v['motions']} | {v['means']['normalized_return']:.8f} |")
        lines += ["",f"全库正式节点 {full_nodes}；末三可用 {tail}，均值 {comparison['tail']['mean_return']}。共同完整集合的XY/SO3/body/joint与奖励分解、hard实际曝光和分组WM误差见逐节点comparison与paired_comparison。",
            "", "结果同时覆盖困难技能、普通动作姿态质量和LAFAN保持；不以完整数或训练loss替代控制质量，不挑最佳节点、不拼接成功。不同replay分布的WM误差不作同输入因果比较。",
            "",f"大产物保留 {run}；不Release、不tar、不在用户电脑归档、不自动清理或延长、不启动P11。"]
        (jobdir/"conclusion.md").write_text("\n".join(lines)+"\n")
        paired_comparisons()
        state=refresh()
        commit=push_results(f"p10-{name}-completed",[campaign.relative_to(ROOT),(ROOT/"results"/run.name).relative_to(ROOT)],lambda idx:index_update(idx,state))
        summary.update(status="completed",lightweight_results_published=True,results_commit=commit,completed_unix=time.time())
        write(jobdir/"summary.json",summary)
        state=refresh()
        p["status"]=state["status"]
        write(PROTOCOL,p)
        push_results(f"p10-{name}-publication-confirmed",[campaign.relative_to(ROOT),PROTOCOL.relative_to(ROOT)],lambda idx:index_update(idx,state))
        print("P10_JOB_COMPLETE",name,final,flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("job")
    finish(parser.parse_args().job)
