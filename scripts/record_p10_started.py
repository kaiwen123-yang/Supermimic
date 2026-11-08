"""Record observed P10 formal progress and publish the actual startup handoff."""
import datetime
import fcntl
import subprocess
from pathlib import Path
from p10_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results


def main():
    p=read(PROTOCOL)
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    campaign=ROOT/"results"/p["campaign"]
    with Path(p["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for name,job in p["jobs"].items():
            run=ROOT/"outputs/runs"/job["run"]
            runtime=read(run/"runtime.json")
            budget=read(run/"budget.json")
            import json
            with (run/"metrics.jsonl").open() as f:
                rows=[json.loads(line) for line in f if line.endswith("\n")]
            latest=rows[-1]
            summary=read(campaign/"jobs"/name/"summary.json")
            summary.update(status="running",training_started=True,pid=runtime["pid"],observed_beijing=now,
                observed_training_iteration=latest["iteration"],observed_stage_seconds=budget["stage_elapsed_seconds"],
                observed_new_joint_updates=latest["new_joint_updates"],observed_new_wm_only_updates=latest["new_wm_only_updates"],
                runtime=runtime,latest_training=latest,next_lafan_iteration=12000,next_bones_iteration=15000)
            write(campaign/"jobs"/name/"summary.json",summary)
            write(campaign/"jobs"/name/"actual_config.json",read(run/"config.json"))
            p["jobs"][name]["status"]="running"
        p.update(status="running",implementation_status="implemented_and_formally_running",training_started=True,started_observed_beijing=now)
        write(PROTOCOL,p)
        resources={"observed_beijing":now,"gpu":subprocess.check_output(["nvidia-smi","--query-compute-apps=pid,process_name,used_memory","--format=csv"],text=True),
            "host_memory":{line.split(":")[0]:line.split(":")[1].strip() for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith(("MemTotal:","MemAvailable:"))},
            "container_memory_limit_bytes":Path("/sys/fs/cgroup/memory.max").read_text().strip(),
            "container_memory_current_bytes":int(Path("/sys/fs/cgroup/memory.current").read_text()),
            "memory_note":"/proc/meminfo is host telemetry; cgroup records the effective container limit and usage separately."}
        write(campaign/"startup_resources.json",resources)
        state=refresh()
        agent=ROOT/"AGENTS.md"
        text=agent.read_text().replace("- 当前P10计划已发布，尚未实施/启动：docs/P10_8K_HARD_PRACTICE_PLAN.md、configs/next_stage_8k_hard_practice_protocol.json、docs/P10_CODEX_START_PROMPT.md。本次用户明确要求推送下一步并扩大环境，旧P9“不自动开P10”不覆盖新的授权。按启动提示词实施时接续P9 full9000，不重新跑P9。",
            f"- P10两路已正式启动并完成真实联合更新，启动核实时间 {now}。入口为docs/P10_8K_HARD_PRACTICE_PLAN.md、configs/next_stage_8k_hard_practice_protocol.json及docs/P10_CODEX_START_PROMPT.md；实际状态见results/{p['campaign']}/summary.json。接续现有sm-p10-full8k-control和sm-p10-full8k-hard，不重复启动P9/P10，不重建活跃replay/LR。")
        agent.write_text(text.replace("## P10实施（计划已发布，尚未启动）","## P10实施（两路已正式运行，接续现有tmux）"))
        plan=ROOT/"docs/P10_8K_HARD_PRACTICE_PLAN.md"
        plan.write_text(plan.read_text().replace("状态：**计划已发布，执行端适配与训练尚未启动**。日期：2026-11-08（北京时间）。",
            f"状态：**必要适配已实现，两路正式训练已启动并完成真实联合更新**。核实时间：{now}。运行索引见[summary.json](../results/{p['campaign']}/summary.json)；正式评分尚未到首节点。"))
        lines=["# P10 正在运行：下一窗口接续", "",f"核实时间：{now}。代码已实施，两路已从P9 full9000完整恢复并执行真实联合更新。", "",
            "先读取本文件、AGENTS.md、P10计划与协议及campaign summary，再只读核实服务器当前状态。P9已完成；P10无需再次请求启动许可，也不要重复启动。", "",
            "服务器：autodl-d57。工作树：/root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice。source activate.sh。", "",
            "| job | tmux | 本次观察iteration | 新阶段秒 | 新增联合更新 |", "|---|---|---:|---:|---:|"]
        for name,s in state["jobs"].items():
            lines.append(f"| {name} | {s['tmux']} | {s['observed_training_iteration']} | {s['observed_stage_seconds']:.3f} | {s['observed_new_joint_updates']} |")
        lines += ["",f"run根目录为outputs/runs/{p['campaign']}-<job>；训练日志为outputs/campaigns/<run>.train.log。活跃进程和最新budget.json/metrics.jsonl为实时依据，本表是带时间快照。", "",
            "每路8192真实环境/8192想象/WM10×4096，source仍LAFAN2048+BONES6144。候选reset分层为2048/5120/1024，control为2048/6144/0；639 hard成员冻结，原两source的memory EMA每来源仍只更新一次。", "",
            "9001–27000或累计新阶段40h先到。每路已填充一次64步replay；不得因交接重建活跃replay、重置LR或重新获得40h预算。实际进程退出才从该run最新checkpoint按--resume-in-place接续，并保留累计budget。", "",
            "LAFAN正式节点12000/15000/18000/21000/24000/27000；全BONES15000/21000/27000。使用阶段偏移iteration-9000，复用父9000评分。实际终点补齐两项；run脚本训练结束后自动调用finish_p10.py。", "",
            "六个固定同动作WM短窗已经完成，结果见campaign evidence/manifest.json；不重复预测，不新跑物理扫描。正式评分、证据与Git发布共享P6的work/p2-publication.lock；训练不持锁。", "",
            "全库按(reference_steps, original_source_clip_id)排序组批1024，输出恢复原ID，终点每组保留原ID最小两个失败尾窗。评价同时看hard、普通姿态质量和LAFAN保持；所有逐clip标量按1000条CSV分片。", "",
            "继续使用现有环境/G1资产/同一P9 CPU只读memmap。不要重建环境、重做数据、测试/benchmark或额外实验。保留其他项目，不停止其他任务。", "",
            "两路tmux跨窗口运行，单交互窗口≤4h。预算结束按真实终点评分发布；不自动延长、Release、tar、本地归档、阶段清理或启动P11。"]
        (ROOT/"docs/P10_CODEX_START_PROMPT.md").write_text("\n".join(lines)+"\n")
        commit=push_results("p10-formal-training-started",[campaign.relative_to(ROOT),PROTOCOL.relative_to(ROOT),
            Path("AGENTS.md"),Path("docs/P10_8K_HARD_PRACTICE_PLAN.md"),Path("docs/P10_CODEX_START_PROMPT.md")],lambda idx:index_update(idx,state))
        print("P10_START_PUBLISHED",commit,flush=True)


if __name__ == "__main__":
    main()
