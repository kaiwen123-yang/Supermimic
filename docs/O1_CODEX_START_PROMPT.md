# O1 Codex 准备提示词

发布时状态：源码比较已经完成；D57官方环境与训练尚未执行。此提示词用于**实施准备工作**，不启动LAFAN/BONES训练或P12。正式训练应使用准备后写明实际配置、有限预算和评测节点的协议。

将下方正文交给可以连接autodl-d57的Codex：

```text
请拉取 https://github.com/kaiwen123-yang/Supermimic 最新main，实施O1官方SuperMimic复现准备，不只重述已有比较报告。

先读AGENTS.md、docs/OFFICIAL_COMPARISON_20261111.md、docs/O1_OFFICIAL_REPRODUCTION_PLAN.md和configs/official_source_inventory_20261111.json。保留LAFAN1指标复现已成功的结论；当前优先O1，P12保留备选，不自动启动或停止其他会话已开始的任务。

本轮是准备：不启动训练、模型推理、完整评分或benchmark，不重跑P6—P11。不要修改既有独立实现的算法。尽可能并行读取相互独立的来源、数据索引和配置；服务器写入顺序清楚，避免争用现有任务。

使用autodl-d57。原项目 /root/autodl-tmp/robot-repro/supermimic 及其.venv、activate.sh、G1资产、数据、checkpoint、工作树、Git/stash与其他项目保留。新建官方工作区 /root/autodl-tmp/robot-repro/supermimic-official-workspace，官方supermimic与mjlab_research按README作为兄弟目录。本轮可以在此新目录建立所需独立环境，不在原环境或Conda base安装/升级。

官方基点是HybridRobotics/supermimic@5efbf114e11f725c31d83e217be987c13c0e4ce2。核对最新公开变化；若作者补充了本计划缺失的依赖、配置、数据或评测入口，记录提交与差异后合理采用。保留上游来源/许可，不通过任意历史日期猜论文版本。

优先解决kevinzakka/mjlab_research的真实来源与匹配版本。审计时地址404，公开mujocolab/mjlab缺motion_ends、root_pos_w/root_quat_w、motion.fk/body_state及external sampler接口。不能仅替换URL或重命名公共包就称兼容；不绕过访问限制，不自动向作者发Issue/邮件。缺失时完成所有能继续的源码/配置/数据准备，明确剩余材料，不启动未知环境。

只有取得匹配研究依赖后，按官方pyproject/uv.lock在新工作区创建Python3.13独立环境并记录实际版本；不复制旧site-packages，不更改旧Python3.11/Torch2.7.1环境。不要新加导入/形状/冒烟/哈希/恢复测试或benchmarks。

明确分开官方当前main基线与论文实验配置。论文v1及v2核心附录仍是Adam、cosine、proprio历史10；当前main有Muon、LayerNorm/GELU和不同默认。默认只读单条lafan_run1_subject5，actor_obs=rep_state、history_length=1，不是完整论文运行。

定位实际论文run config、GenCoord/MaxCoord选择、权重入口和数据清单。若无法确认原主结果版本，准备明确命名的当前main GenCoord/proprio/history10基线，不虚称历史配置已恢复。旧模型不能直接当官方checkpoint；不移入XYZ713、hard配额、存活加权Critic、BCE或P11局部高度修正。

读取现有LAFAN40及BONES manifest/索引，确定官方loader需要的关节顺序、坐标、fps、字段和成员映射。只做必要格式适配，不重复下载/retarget/全库打包或复制约45GiB数据。论文129514条与本项目130394条成员尚未证明相同，不能任意删880条凑数。没有作者成员清单时如实标注数据差异。

定位完整动作评测入口。benchmark.py是吞吐测速，play.py是交互回放；若作者未提供评分脚本，只设计或实现以官方真实环境与Actor处理为基础的最小适配，不在本轮执行评分。评测从frame0到真实失败/自然末尾，确定性、无DR/噪声、摩擦1，完整参考时长作分母；所有clip和失败保留。不得改奖励/终止制造成绩。

落实本地权重保存与轻量Git发布方案。当前上游仅存网络权重，wandb_run_path只加载WM，不是完整resume；不把已有恢复能力写得比源码更强。避免默认大checkpoint上传和版本清理影响用户产物约定。必要产物适配与算法保持分开，不新建通用发布/归档平台。

准备完成后提交真实准备状态、来源版本、最小本地改动、数据/评测契约，以及下一轮准确训练命令和有限预算/评测节点的草案；没有可运行依赖时明确标记阻塞，不生成假命令冒充已可运行。第一条正式方案是完整LAFAN40，再推进BONES；本轮不启动两者，不自动加seed、PPO、双GPU或实机。

单Codex窗口<=4h。不要停止别的训练/评分/存储任务，不因交接重建活跃replay或重置LR。代码、实际配置、状态和计划推GitHub；大数据/权重/日志留服务器，不Release、tar、自动删除或在我电脑归档。H盘迁移是另一项任务，本轮不执行。遇到具体运行错误再针对修复，不增加防御性代码或无关扫描。
```

准备工作的完成标准是实际材料、环境与入口状态清楚；它不是新的成绩验收门槛，也不授权无限期运行或跳过真实依赖缺口。

