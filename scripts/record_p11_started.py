"""Publish the observed P11 startup, actual implementation and parent evidence."""
import datetime
import fcntl
import json
import re
import subprocess
from pathlib import Path
from p11_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_p11 import push_results

IMPLEMENTATION = [
    "supermimic/networks.py", "supermimic/learning.py", "supermimic/hard_exposure.py",
    "supermimic/rollout_evidence.py", "scripts/train.py",
    "scripts/start_p11.py", "scripts/run_p11_d57.sh", "scripts/publish_p11.py",
    "scripts/publish_p11_d57.sh", "scripts/finish_p11.py", "scripts/p11_results.py",
    "scripts/p11_evidence.py", "scripts/record_p11_started.py",
    "configs/bones_full_lafan_p11_full8k_residual_control.json",
    "configs/bones_full_lafan_p11_full8k_velocity_height.json",
    "configs/next_stage_root_height_protocol.json",
    "AGENTS.md", "README.md", "docs/P11_ROOT_HEIGHT_CONSISTENCY_PLAN.md", "docs/P11_CODEX_START_PROMPT.md",
]


def main():
    p=read(PROTOCOL)
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    campaign=ROOT/"results"/p["campaign"]
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for name,job in p["jobs"].items():
            run=ROOT/"outputs/runs"/job["run"]
            runtime=read(run/"runtime.json")
            with (run/"metrics.jsonl").open() as stream:
                latest=[json.loads(line) for line in stream if line.endswith("\n")][-1]
            summary=read(campaign/"jobs"/name/"summary.json")
            summary.update(status="running",training_started=True,pid=runtime["pid"],observed_beijing=now,
                startup_training_snapshot=latest,runtime=runtime,next_lafan_iteration=30000,next_bones_iteration=30000)
            write(campaign/"jobs"/name/"summary.json",summary)
            write(campaign/"jobs"/name/"actual_config.json",read(run/"config.json"))
            p["jobs"][name].update(status="running",implementation_status="implemented_and_formally_running",training_started=True)
        p.update(status="running",implementation_status="implemented_and_formally_running",training_started=True,
            started_observed_beijing=now)
        write(PROTOCOL,p)
        resources={"observed_beijing":now,
            "gpu":subprocess.check_output(["nvidia-smi","--query-compute-apps=pid,process_name,used_memory","--format=csv"],text=True),
            "cgroup":{"memory_max":Path("/sys/fs/cgroup/memory.max").read_text().strip(),
                "memory_current":int(Path("/sys/fs/cgroup/memory.current").read_text()),
                **{key:int(value) for key,value in (line.split() for line in Path("/sys/fs/cgroup/memory.stat").read_text().splitlines())
                    if key in ("anon","file","inactive_file")}},
            "memory_note":"Effective container limit and usage; file/inactive_file are cache, not anonymous training allocation."}
        state=refresh()
        resources["training_memory"]={name:{k:v for k,v in job["latest_training"].items()
            if k in ("torch_allocated_mib","torch_reserved_mib","torch_peak_allocated_mib","collection_seconds","world_seconds","policy_critic_seconds")}
            for name,job in state["jobs"].items()}
        write(campaign/"startup_resources.json",resources)
        path=ROOT/"AGENTS.md"
        text=path.read_text()
        text=re.sub(r"^- \*\*P11当前.*$", f"- **P11两路已实施并正式并行运行。** 启动核实时间 {now}；实际状态见results/{p['campaign']}/summary.json。接续现有sm-p11-residual和sm-p11-velocity-height，不重复启动P10/P11，不重建活跃replay或重置LR。两路同P10 hard27000完整resume，仅比较root-z残差与同次预测速度梯形高度；各8192/8192/WM10×4096，原hard配额，新增9000联合更新或累计20h，到36000；全BONES/LAFAN节点30000/33000/36000及实际终点。父七窗224步预测已完成，终点两WM各同输入一次。",text,flags=re.M)
        text=text.replace("## P11实施（当前计划；启动后按实际状态更新）","## P11实施（两路已正式运行，接续现有tmux）")
        path.write_text(text)
        path=ROOT/"README.md"
        path.write_text(path.read_text().replace("P11 根高度与预测垂直速度一致性研究，计划已发布，尚未实施/启动。",
            "P11 根高度与预测垂直速度一致性研究，两路已正式并行运行。"))
        path=ROOT/"docs/P11_ROOT_HEIGHT_CONSISTENCY_PLAN.md"
        path.write_text(path.read_text().replace("状态：**计划已整理发布；实现与服务器训练尚未启动。** 日期：2026-11-10（北京时间）。",
            f"状态：**实现与父七窗预测已完成，两路已正式并行训练并完成真实联合更新。** 核实时间：{now}。实时依据为服务器run日志；[启动快照](../results/{p['campaign']}/summary.json)。"))
        lines=["# P11 正在运行：下一窗口接续","",f"核实时间：{now}。两路已从P10 hard27000完整恢复并执行真实联合更新。P10已完成，不重复启动。","",
            "服务器autodl-d57；工作树/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency；source activate.sh。",
            "", "先读取AGENTS.md、P11计划/协议和campaign summary，再读取现有tmux及run下budget.json、metrics.jsonl。保留当前活跃进程、replay和LR。",
            "", "| job | tmux | 观察iteration | 新增联合更新 | 新阶段秒 |", "|---|---|---:|---:|---:|"]
        for name,s in state["jobs"].items():
            lines.append(f"| {name} | {s['tmux']} | {s['observed_training_iteration']} | {s['observed_new_joint_updates']} | {s['observed_stage_seconds']:.3f} |")
        lines += ["",f"运行目录：outputs/runs/{p['campaign']}-<job>；日志outputs/campaigns/<run>.train.log。表中为带时间快照。",
            "", "两路8192真实/8192想象/WM10×4096，k8/H32、原12.5%hard reset配额与其他配方保持。唯一变量world_root_height_mode=residual或velocity_trapezoid。后者z_next=z+.01*(vz+predicted_vz_next)，下一vz来自同次WM。",
            "", "每路27001–36000或累计新阶段20h先到。已各填充一次64步replay；不因交接重新填充或重新获得预算。仅真实进程退出才按该run最新checkpoint与--resume-in-place继续。",
            "", "全BONES和LAFAN共同节点30000/33000/36000及实际终点。复用父27000评分；原1024长度排序评分、完整逐clip CSV、同次尾窗保持。训练脚本自动请求publish_p11，结束后run脚本自动调用finish_p11。",
            "", "父固定七窗已完成7条/224预测步：evidence/parent_hard27000。终点各WM只对相同输入再做一次，总21条/672步。不要重跑父证据、新物理或扫描起点。候选残差为零不算成功；比较真实预测误差、控制、保持。",
            "", "GPU证据/评分/Git发布共用P6 work/p2-publication.lock，总并发1；训练不持锁。每训练/评分Torch2线程，两路8k，不增加第三learner。正常节点记录cgroup anon/file/inactive_file及GPU占用。",
            "", "LAFAN达到0.82的既有复现成功保持。预算结束如实评分发布，不延长、安装升级、测试/benchmark、Release、tar、本地归档、自动阶段清理或开P12。大产物留服务器，用户备份未确认。"]
        (ROOT/"docs/P11_CODEX_START_PROMPT.md").write_text("\n".join(lines)+"\n")
        commit=push_results("p11-formal-training-started",[Path(x) for x in IMPLEMENTATION]+[campaign.relative_to(ROOT)],lambda idx:index_update(idx,state))
        print("P11_START_PUBLISHED",commit,flush=True)


if __name__ == "__main__":
    main()
