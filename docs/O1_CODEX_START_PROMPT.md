# O1 Codex 官方复现执行提示词

用户于2026-11-11确认：下一步专心复现官方代码。此提示词替代此前“仅准备、不训练”的版本。执行更新：D57官方源码工作区、LAFAN40引用和逐动作索引已落地，研究依赖仍404，环境/训练/评分未启动。先读[最新执行交接](O1_EXECUTION_HANDOFF_20261111.md)，复用已有准备，不重新克隆或重建数据；P12及独立实现的新实验暂缓。

将下方正文交给可以连接autodl-d57的Codex：

```text
请拉取 https://github.com/kaiwen123-yang/Supermimic 最新main，按O1执行官方SuperMimic复现。当前唯一新增实验主线是官方代码；不要继续P12或为旧实现增加改法。先读AGENTS.md、docs/O1_OFFICIAL_REPRODUCTION_PLAN.md、docs/OFFICIAL_COMPARISON_20261111.md和configs/official_source_inventory_20261111.json，随后实际推进，不重复上一轮完整审计。

目标是连续完成必要环境/数据/评测准备，并在条件具备后直接开展第一段完整LAFAN40官方训练、评分和轻量发布。之前“只准备、不训练”的限制已被这次执行计划替代，不要因此停在建议或再次询问是否开始。尚未取得的真实依赖不能伪装成已解决。

使用autodl-d57，复用 /root/autodl-tmp/robot-repro/supermimic-official-workspace 已有官方源码与data/lafan40_existing50hz引用，先读docs/O1_EXECUTION_HANDOFF_20261111.md。supermimic与待取得的mjlab_research按官方README作为兄弟目录，取得匹配依赖后使用独立Python3.13环境。原项目 /root/autodl-tmp/robot-repro/supermimic 的环境、数据、G1资产、工作树、Git/stash及checkpoint保留；不修改Conda base、MPC-RL、π系列或其他任务，不停止任何已有训练/评分/迁移。

本次固定官方HybridRobotics/supermimic@5efbf114e11f725c31d83e217be987c13c0e4ce2，后续若上游补齐依赖/配置，记录变化后采用。先落实kevinzakka/mjlab_research的可访问来源及匹配版本。该依赖本次仍404，Issue#1只有其他用户询问公共mjlab，无作者确认的替代commit。不能直接重命名公共mjlab、猜测缺失接口或绕过访问限制，也不自动向作者发Issue/邮件。

若依赖仍不可取得，完成不依赖它的源码落地、实际数据索引整理、运行配置和最小评测/保存适配设计，推送状态与精确缺失项；不安装一套猜测环境、不假报跑通、不转去旧P12。取得匹配依赖后按官方pyproject/uv.lock在新目录建立环境，原.venv和base不动。

首条正式运行是完整LAFAN40，seed=0，run_name=o1-official-lafan40-s0。优先使用作者确切实验配置；若无法取得历史主配置，就明确标注为当前官方main GenCoord/proprio/history10基线，保留该版本整体算法。默认单条lafan_run1_subject5和rep_state/history1不代表论文完整实验。原网络checkpoint不续入，不加入XYZ713、hard配额、存活加权Critic、BCE或P11局部z修正。

复用现有LAFAN40原始/工作数据与manifest，只根据取得的真实官方loader转换必要字段、关节顺序、坐标和fps。不重复下载/retarget/打包全库。BONES本项目130394条与论文129514条成员尚未对齐，先保留索引，不删880条凑数；本段完成后再安排BONES正式训练。

正式评测必须基于官方真实环境、Actor观测与normalizer，从frame0执行到原硬失败或自然末尾，确定性、摩擦1、无DR和噪声，回报按完整参考时长归一化。优先作者评分入口；若未提供，做必要的最小适配。benchmark.py和play.py不能代替完整评分，不改奖励/阈值制造成绩。保留所有40条的成绩和失败。

第一段上限累计训练12h，或上游配置的迭代上限先到。训练正常初始化/必要replay填充计入；安装、数据准备、评分和发布另记。约3h/6h/12h及实际较早终点保存固定checkpoint并完整评分。任一正式节点R>=.82即保存达标权重与全部成绩并结束本段；否则到预算终点如实交付，不自动续加时间/seed/算法变体。12h是本次工作预算，不是H100论文耗时门槛。既有独立实现LAFAN已达标结论保持，不新增40/40验收要求。

一条官方训练run用独立tmux；资料、索引、适配和统计可并行，不用多开learner占满显存。单Codex交互<=4h，后台跨窗口连续，不因交接停止训练、重建活跃replay或重置LR。记录真实采样、学习更新计数、共享GPU条件和耗时，不混用官方collection轮与旧联合更新轮。

落实本地模型保存和轻量Git发布。当前官方只存网络权重，wandb_run_path只预载WM，不是完整resume；需要恢复时只做实际必要的状态保存/加载并如实说明边界。避免默认大checkpoint上传/版本清理破坏用户产物约定。必要保存、评分、运行预算适配与核心算法分开记录。

不新增防御性框架、单元/mock/冒烟/导入/形状/哈希测试、恢复演练、benchmark、无关扫描或参数搜索。完成必要适配后直接进行本计划正式训练与评分，真实错误再针对定位。代码、实际配置、全部轻量逐动作评分、关键统计、真实状态和结论推GitHub；大权重/轨迹/视频/日志留服务器，不自动Release、tar、归档到本机或删除原件。H盘迁移为另一任务，不介入。

交付明确区分：已取得源码、依赖是否就绪、实际环境、训练是否启动/结束、正式成绩、剩余缺口。首段结果发布后给出BONES接续所需的具体配置和预算，不自动重跑旧实验或拓展实机。
```
