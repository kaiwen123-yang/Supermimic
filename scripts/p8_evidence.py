"""Exactly eight stored-action physical rolls and eight C42000 WM windows."""
import fcntl
import sys
import numpy as np
from pathlib import Path
from p8_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results
from p7_evidence import world_windows
from position_feedback_metrics import COMPONENTS


def physical_rolls(protocol, output):
    sys.path.insert(0, str(ROOT))
    import torch
    import warp as wp
    from supermimic.simulator import G1Simulator
    from supermimic.kinematics import ForwardKinematics
    from supermimic.task import reward_and_termination
    from supermimic.geometry import quat_mul, quat_inv, quat_to_rotvec
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    sim = G1Simulator(4)
    fk = ForwardKinematics(sim.host_model).float().cuda()
    summaries = []
    for milestone in (39000, 42000):
        source = ROOT / "results/20261105-p7-feedback-reproduction-s0-continuation/milestones" / f"iteration_{milestone:07d}/selected_rollouts.npz"
        with np.load(source) as z:
            pred = torch.tensor(z["predicted_state"], device="cuda")
            context = torch.tensor(z["context"], device="cuda")
            actions = torch.tensor(z["action"], device="cuda")
            ref_q = torch.tensor(z["reference_qpos"], device="cuda")
            ref_v = torch.tensor(z["reference_qvel"], device="cuda")
            sim.reset(pred[0, :, :36], pred[0, :, 36:71])
            sim.context.copy_(context)
            ids = torch.arange(4, device="cuda")
            wp.to_torch(sim.model.geom_friction)[ids[:, None], torch.tensor(sim.foot_ids, device="cuda")[None, :], 0] = context[:, :1]
            wp.to_torch(sim.model.body_ipos)[ids, sim.torso_id] = sim.nominal_ipos[sim.torso_id] + context[:, 30:]
            state = pred[0].clone()
            states = [state]
            records = {key: [] for key in ("real_reward", "predicted_reward", "real_components", "predicted_components", "real_height_error", "predicted_height_error", "real_tilt_error", "predicted_tilt_error", "real_hard_done", "predicted_hard_done")}
            for t in range(32):
                q, v = sim.step(actions[t])
                ref = {"qpos": ref_q[t+1], "qvel": ref_v[t+1], **fk(ref_q[t+1], ref_v[t+1])}
                real = torch.cat((q, v, actions[t]), -1).clone()
                for label, current, previous in (("real", real, state), ("predicted", pred[t+1], pred[t])):
                    reward, done, metrics = reward_and_termination(fk(current[:, :36], current[:, 36:71]), ref,
                        current[:, :36], actions[t], previous[:, 71:], sim.soft_lower, sim.soft_upper)
                    done |= ~(torch.isfinite(current).all(-1) & torch.isfinite(reward))
                    records[label+"_reward"].append(reward)
                    records[label+"_components"].append(metrics["components"])
                    records[label+"_height_error"].append(metrics["root_height_error_m"])
                    records[label+"_tilt_error"].append(metrics["tilt_error"])
                    records[label+"_hard_done"].append(done)
                states.append(real)
                state = real
            actual = torch.stack(states)
            arrays = {key: torch.stack(value).cpu().numpy() for key, value in records.items()}
            errors = {"root_position_error_m": (actual[1:, :, :3]-pred[1:, :, :3]).norm(dim=-1),
                "root_SO3_error_rad": quat_to_rotvec(quat_mul(pred[1:, :, 3:7], quat_inv(actual[1:, :, 3:7]))).norm(dim=-1),
                "joint_position_rmse_rad": (actual[1:, :, 7:36]-pred[1:, :, 7:36]).square().mean(-1).sqrt(),
                "qvel_rmse": (actual[1:, :, 36:71]-pred[1:, :, 36:71]).square().mean(-1).sqrt()}
            arrays.update({key: value.cpu().numpy() for key, value in errors.items()})
            valid = np.concatenate((np.ones((1, 4), dtype=bool), np.cumprod(~arrays["real_hard_done"], axis=0)[:-1].astype(bool)))
            iteration = int(z["iteration"])
            path = output / f"update_{iteration}_four_stored_action_physics.npz"
            np.savez_compressed(path, actual_state=actual.cpu().numpy(), valid_transition_through_first_done=valid,
                **arrays, **{key: z[key] for key in z.files})
            summary = {"source": str(source), "source_update": iteration, "npz": str(path.relative_to(ROOT)),
                "rollouts": [], "reward_component_order": list(COMPONENTS), "dt": .02,
                "context": "Stored friction, calibration and COM applied to both sim.context and physical friction/body_ipos; no new randomized reset.",
                "scope": "32 stored actions, no Actor calls; values/targets from original imagined update only. Posttermination transitions saved but excluded from episode interpretation."}
            for i in range(4):
                hits = np.flatnonzero(arrays["real_hard_done"][:, i])
                summary["rollouts"].append({"motion": str(z["motion"][i]), "start_frame": int(z["start_frame"][i]),
                    "first_real_termination_step": int(hits[0])+1 if len(hits) else None,
                    "horizons": {str(h): {**{key: float(arrays[key][h-1, i]) for key in errors},
                        "within_valid_episode": bool(valid[h-1, i]), "real_reward_sum_valid": float(arrays["real_reward"][:h, i][valid[:h, i]].sum()),
                        "predicted_reward_sum_same_valid_steps": float(arrays["predicted_reward"][:h, i][valid[:h, i]].sum())} for h in (8, 16, 32)}})
            write(path.with_suffix(".json"), summary)
            summaries.append(summary)
    return summaries


def main():
    protocol = read(PROTOCOL)
    output = ROOT / "results" / protocol["campaign"] / "evidence"
    output.mkdir(parents=True, exist_ok=True)
    with Path(protocol["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        write(output / "manifest.json", {"status": "running"})
        import torch
        with torch.no_grad():
            physical = physical_rolls(protocol, output)
        source_run = Path(protocol["source"]["checkpoint"]).parent
        score = read(ROOT / protocol["source"]["evaluation"])
        spec = {"source_server_run": str(source_run), "model_windows": {"checkpoint": protocol["source"]["checkpoint"]},
            "current_failure_windows": [{"motion": r["motion"], "state_frames_inclusive": [max(0, r["executed_steps"]-132), r["executed_steps"]]} for r in score["clips"] if r["failed"]]}
        windows = world_windows(spec, output / "C42000_world_model", evaluation_iteration=42000)
        manifest = {"status": "computed", "physical_rollouts": 8, "world_model_windows": 8,
            "physical": [{"source_update": s["source_update"], "npz": s["npz"]} for s in physical],
            "world": [{k: s[k] for k in ("motion", "npz", "start_frame", "covers_terminal_step")} for s in windows]}
        write(output / "manifest.json", manifest)
        lines = ["# P8 指定机制短证据", "", "已完成38089/41379各4条同动作物理展开与C42000四个失败各2个WM窗。", "",
            "| 更新 | 动作 | 首次真实终止步 | H32根位置误差m | H32仍属有效episode |", "|---|---|---:|---:|---|"]
        for s in physical:
            for r in s["rollouts"]:
                lines.append(f"| {s['source_update']} | {r['motion']} | {r['first_real_termination_step']} | {r['horizons']['32']['root_position_error_m']:.6f} | {r['horizons']['32']['within_valid_episode']} |")
        lines += ["", "| 当前失败动作 | 起点帧 | H32根位置误差m | 预测解析终止概率 | 真实终止 |", "|---|---:|---:|---:|---|"]
        for s in windows:
            h = s["horizons"]["32"]
            lines.append(f"| {s['motion']} | {s['start_frame']} | {h['root_position_m']:.6f} | {h['predicted_analytic_smooth_probability']:.6f} | {h['actual_termination']} |")
        lines += ["", "比较限于指定初态/context与已存动作；不是闭环策略评分或梯度因果证明。H16/H32判断等待完整正式评分。完整数据与8/16/32步结果见配套NPZ/JSON。"]
        (output / "conclusion.md").write_text("\n".join(lines)+"\n")
        campaign = refresh()
        result = output.parent
        commit = push_results("p8-prescribed-evidence", [result.relative_to(ROOT)], lambda index: index_update(index, campaign))
        manifest.update(status="published", results_commit=commit)
        write(output / "manifest.json", manifest)
        campaign = refresh()
        push_results("p8-prescribed-evidence-confirmed", [result.relative_to(ROOT)], lambda index: index_update(index, campaign))
        print("P8_EVIDENCE_COMPLETE", commit, flush=True)


if __name__ == "__main__":
    main()
