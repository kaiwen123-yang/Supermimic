# P10 正在运行：下一窗口接续

核实时间：2026-11-08T17:19:17.686075+08:00。代码已实施，两路已从P9 full9000完整恢复并执行真实联合更新。

先读取本文件、AGENTS.md、P10计划与协议及campaign summary，再只读核实服务器当前状态。P9已完成；P10无需再次请求启动许可，也不要重复启动。

服务器：autodl-d57。工作树：/root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice。source activate.sh。

| job | tmux | 本次观察iteration | 新阶段秒 | 新增联合更新 |
|---|---|---:|---:|---:|
| full8k_control | sm-p10-full8k-control | 9035 | 242.389 | 35 |
| full8k_hard_practice | sm-p10-full8k-hard | 9025 | 182.926 | 25 |

run根目录为outputs/runs/20261108-p10-8k-hard-practice-s0-<job>；训练日志为outputs/campaigns/<run>.train.log。活跃进程和最新budget.json/metrics.jsonl为实时依据，本表是带时间快照。

每路8192真实环境/8192想象/WM10×4096，source仍LAFAN2048+BONES6144。候选reset分层为2048/5120/1024，control为2048/6144/0；639 hard成员冻结，原两source的memory EMA每来源仍只更新一次。

9001–27000或累计新阶段40h先到。每路已填充一次64步replay；不得因交接重建活跃replay、重置LR或重新获得40h预算。实际进程退出才从该run最新checkpoint按--resume-in-place接续，并保留累计budget。

LAFAN正式节点12000/15000/18000/21000/24000/27000；全BONES15000/21000/27000。使用阶段偏移iteration-9000，复用父9000评分。实际终点补齐两项；run脚本训练结束后自动调用finish_p10.py。

六个固定同动作WM短窗已经完成，结果见campaign evidence/manifest.json；不重复预测，不新跑物理扫描。正式评分、证据与Git发布共享P6的work/p2-publication.lock；训练不持锁。

全库按(reference_steps, original_source_clip_id)排序组批1024，输出恢复原ID，终点每组保留原ID最小两个失败尾窗。评价同时看hard、普通姿态质量和LAFAN保持；所有逐clip标量按1000条CSV分片。

继续使用现有环境/G1资产/同一P9 CPU只读memmap。不要重建环境、重做数据、测试/benchmark或额外实验。保留其他项目，不停止其他任务。

两路tmux跨窗口运行，单交互窗口≤4h。预算结束按真实终点评分发布；不自动延长、Release、tar、本地归档、阶段清理或启动P11。
