# SuperMimic 独立复现

> **验收结论：LAFAN1指标复现成功。** 用户确认以达到作者对应实验指标为准；P6 B33000全40正式评估回报0.86624655，超过论文0.82。P7及后续研究不撤销该项已达标结论，整篇论文的规模与效率证据另行区分。[依据](results/20261105-p6-position-feedback-s0/review_20261105.json)。

> **当前主线：O2官方完整BONES。** 训练已结束，等待评分（training_completed_evaluation_pending）。BONES-only 130394条、seed0从零、4096环境；累计12h或1000000 collection先到停止，无回报早停。训练子进程退出后依次评分全部实际节点的BONES与LAFAN40。状态见results/20261111-o2-official-bones-s0/summary.json，接续见docs/O2_EXECUTION_HANDOFF.md。tmux sm-o2-official-bones-s0；保持活跃状态和累计预算，不重启replay/LR。O1成果保留，P12继续暂停。

> **O1官方LAFAN40首段已完成并复核。** seed0从零训练，首个约3h正式节点 **R=0.85882311、39/40**；约3h8m17s实际终点 **R=0.87443989、40/40**，已达到0.82目标并正常停止。全40根XY时间均值0.765250m，完成率与跟踪精度分别报告。[完整复核](docs/O1_REVIEW_20261111.md)、[派生统计](results/20261111-o1-official-lafan40-s0/review_20261111.json)、[全部正式节点](results/20261111-o1-official-lafan40-s0/summary.json)、[逐动作成绩](results/20261111-o1-official-lafan40-s0/README.md)、[接续说明](docs/O1_OFFICIAL_RUN_20261111.md)。O1不补6h/12h或追加预算；新O2按本轮独立方案推进。

> **P11已全部完成并复核。** 原残差终点全BONES **R=.86375135、129152/130394完整、hard312/639**；高度约束 **R=.85693786、129598完整、hard305/639**。候选多完成446条，但普通质量和同输入WM预测较差；两路flip0/44、handstand0/160，LAFAN终点均29/40。候选在部分中间节点/LAFAN跨节点保持有优势，不能概括成全面退化。原WM在有效存活前缀就有误差积累；P12据此研究拟合窗口，不将预测误差等同于已证明梯度错误。[完整复核与论文逐项指标](docs/P11_REVIEW_20261111.md)、[派生数据](results/20261110-p11-root-height-consistency-s0/review_20261111.json)、[已完成结果](results/20261110-p11-root-height-consistency-s0/summary.json)。

> **P10已全部完成。** control全BONES **R=.86659060、129579/130394完整**；hard **R=.85921480、129516完整**，固定hard成功 **298/639**、侧滚 **21/22**、侧手翻 **85/120**，但flip **0/44**、handstand **0/160**。普通质量相比父模型恢复；困难加练有明确收益及general/LAFAN代价。P10发现有效想象轨迹的高度与速度不一致；P11已完成相应对照，结果以顶部新复核为准。[详细论文与结果复核](docs/P10_REVIEW_20261110.md)、[派生数据](results/20261108-p10-8k-hard-practice-s0/review_20261110.json)、[已完成结果](results/20261108-p10-8k-hard-practice-s0/summary.json)。

> **P9已全部完成。** LAFAN原Critic60000为 **0.89043870、38/40**，加权为0.84312458、36/40；BONES完整 **130394条/264.430633h** 已训练，9000终点 **R=0.84379710、129220完整、1174失败**，LAFAN保持29/40、起身0/6。数值污染得到处理，但加权未在LAFAN终点获胜；全库普通姿态质量、困难技能和保持仍需提高。[详细复核与论文逐项对照](docs/P9_REVIEW_20261108.md)、[派生数据](results/20261107-p9-critic-full-scale-s0/review_20261108.json)、[已完成结果](results/20261107-p9-critic-full-scale-s0/summary.json)。

> **P8已完成训练、正式评分和轻量发布。** H32终点0.86980516/37成功，H16为0.73023952/31成功；BONES40迁移增加完整数但降低回报，最终LAFAN保持10/40。见[完整结论](results/20261106-p8-stability-scale-s0/conclusion.md)与[结果索引](results/20261106-p8-stability-scale-s0/summary.json)。不重复启动或延长P8。

> **P7已完成训练、正式评分、关键证据和轻量发布。** continuation C42000为回报0.85912099、36/40、完成96.6163%、起身4/6；fresh F9000为0.52562120、20/40、起身0/6，约10h内未达0.82。续训33/40动作回报提高，末三共同成功31→33，但两个起身丢失使终点整体回报低于B33000。见[完成状态](results/20261105-p7-feedback-reproduction-s0/summary.json)、[全部节点结论](results/20261105-p7-feedback-reproduction-s0/conclusion.md)与[P7历史计划](docs/P7_CONTINUATION_AND_FRESH_PLAN.md)。不重复启动P7。

> **P5已完成训练、正式评分和关键结果发布。** 固定24000：A为34/40、回报0.713134、起身6/6；B为34/40、回报0.755425、起身3/6、平均完成96.2842%，保留父32成功中的30条。B是已完成P6的父模型，A保留为历史起身参考；不能说B所有精度/波动都更好。历史[深读复核与P6依据](docs/P6_POSITION_FEEDBACK_PLAN.md)、[分项数据](results/20261104-p5-actor-stability-s0/review_20261105.json)、[P5最终分析](results/20261104-p5-actor-stability-s0/conclusion.md)。

> **当前产物约定：** 先推代码、实际配置、完整逐动作/逐回合评分JSON、关键训练区间统计与结论并继续研究。用户本轮授权的少量失败/成功短窗、指定WM预测、局部日志与正常训练样本作为关键分析证据进Git；完整逐轮日志、大checkpoint、完整视频、完整原始数组/轨迹和缓存留服务器，不上传Release、不进后台大文件队列、不在用户电脑归档。用户自行备份不作为助手发布后的步骤，助手不自动删除或标记已备份；训练原有checkpoint滚动保留照旧。P4已于2026-11-04 02:55完成正式评估和轻量发布，P5已接入按arm隔离的轻量发布、共享评估锁和自动收尾。

> **P4本段训练和正式评估已结束。** P4 `20261103-c0-continuation-s0`：第18000轮，32/40完整执行，完整时长归一化回报0.70675374；起身3/6、跑步4/4。新增9000次联合更新，训练阶段10.198小时（含一次64步预热）。父版本29条成功保留25条，新增完成7条，退化4条。训练、评估、轻量发布及服务器产物位置见[结果](results/20261103-c0-continuation-s0/summary.json)与[逐动作变化](results/20261103-c0-continuation-s0/comparison.json)。该阶段不作为收敛证明，coverage不是论文成功率。大产物留服务器待用户备份和删除，不阻塞本阶段完成。

本仓库用于以学习为目的，依据论文独立实现 **SuperMimic: Scaling Humanoid Whole-Body Control with One Differentiable World Model**。当前已接入固定版本的 LAFAN1 40 条完整动作、G1 / MuJoCo Warp、可微运动学、SuperMimic 核心训练循环、PPO-Sim 和完整动作评估。实际运行结果见 `results/index.json`；源码实现、短程更新和复现成绩分别记录。

- 论文：[arXiv:2610.28480v1](https://arxiv.org/abs/2610.28480v1)
- 作者项目：[supermimic.github.io](https://supermimic.github.io/)
- 当前路线：保留G1 + MuJoCo Warp独立实现及已达到的LAFAN1效果；官方LAFAN40基线已完成，当前发布O2官方BONES完整库执行方案与启动词，尚未实施或启动，P12及独立实现新实验暂缓。
- 本仓库属于用户复现项目，不是作者官方仓库。O1实际使用[官方核心源码](https://github.com/HybridRobotics/supermimic/tree/abc124c1bd5976341034668af3d12c087f2f1f55)及[作者研究环境](https://github.com/HybridRobotics/mjlab_research/tree/dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd)，在相邻独立工作区运行，未混入既有独立训练实现。初始5efbf114源码比较保留供溯源，研究依赖已取得，旧地址404不再阻塞。论文历史精确run配置和BONES筛选成员仍未取得，当前结果明确标为官方当前源码GenCoord/proprio/history10基线。论文最新[v2](https://arxiv.org/pdf/2610.28480v2)的核心方法与实验附录已核对，未实质改变原v1配方。

## D57 环境

SSH 别名 `autodl-d57`；项目目录 `/root/autodl-tmp/robot-repro/supermimic`。O1记录GPU为单张 RTX PRO 6000 Blackwell Server Edition 96GB，官方工作区为 `/root/autodl-tmp/robot-repro/supermimic-official-workspace`。

2026-11-01 重启后，本地数据盘 `/root/autodl-tmp` 已生效为 1000G；西北B区文件存储 `/root/autodl-fs` 已启用并通过读写核验。训练和暂存仍使用本地数据盘，不自动把大产物复制到独立计费的文件存储。

**2026-11-01 21:00 状态：D57 最新主源码、原版本独立 `.venv` 和 G1 机器人资产已恢复。** 79 个包的版本逐项与清理前一致，依赖检查通过，机器人 XML 及 manifest 的 SHA256 与清理前一致。可以正常激活下述开发环境；40 条动作数据缓存及历史权重仍保留在备份中，实际训练/评估前按需恢复。详见 [环境恢复核验](results/storage_cleanup/20261101/development_environment_restored.json)。数据恢复入口为 [RESTORE.md](results/storage_cleanup/20261101/RESTORE.md)，归档见 [GitHub Release](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-d57-storage-archive-20261101)。

```bash
cd /root/autodl-tmp/robot-repro/supermimic
source activate.sh
```

历史安装入口（当前环境已恢复，下一轮不执行）：
```bash
bash scripts/setup_d57.sh
```

`pyproject.toml` / `uv.lock` 固定独立实现环境，Python 3.11，Torch 2.7.1+cu128，MuJoCo / MuJoCo Warp 3.17.0。O1官方工作区已另建Python3.13.18、Torch2.14.0、MuJoCo/mujoco-warp3.16.0、Warp1.18.0环境，研究版mjlab源码已取得；[实际版本](results/20261111-o1-official-lafan40-s0/environment.json)与[接入说明](docs/O1_OFFICIAL_RUN_20261111.md)记录了新依赖和旧锁的处理，没有覆盖独立实现环境。

每套项目使用独立 `.venv` 和 pip，不继承 Conda base、MPC-RL 或 π 系列的包。源码、模型、数据、输出和缓存分别存放。GPU 显存与算力仍属于共享硬件，启动计算前核对实际任务安排。

## 现有内容

- [论文配置](configs/paper_reference.toml)：按论文标注来源的算法/网络/训练参数，不是已经可执行的训练配置。
- [当前O2官方BONES方案](docs/O2_OFFICIAL_BONES_PLAN.md)、[O2协议](configs/o2_official_bones_protocol.json)、[O2 Codex启动词](docs/O2_CODEX_START_PROMPT.md)：方案已发布、适配与训练尚未开始；复用保留的P9 qpos/qvel，源offset441140到packed0、47727908帧，转换为作者已有六字段packed格式，静态参考约12.624GiB。不重新准备原始数据或重写训练loader。
- [O1完成复核](docs/O1_REVIEW_20261111.md)、[官方源码比较](docs/OFFICIAL_COMPARISON_20261111.md)、[已执行O1计划](docs/O1_OFFICIAL_REPRODUCTION_PLAN.md)、[O1完成交接](docs/O1_CODEX_START_PROMPT.md)：官方LAFAN40已完成，旧O1启动提示词不再作为重跑指令；新的BONES执行范围由独立O2启动词给出。
- [备选P12分析与计划](docs/P12_WORLD_WINDOW_PLAN.md)：两路8192完整库以同父k8/k16比较WM拟合窗口，保留H32及原残差；[P12协议](configs/next_stage_world_window_protocol.json)、[P12启动词](docs/P12_CODEX_START_PROMPT.md)、[P11完整复核](docs/P11_REVIEW_20261111.md)。本次不执行P12。
- [已完成P10分析与计划](docs/P10_8K_HARD_PRACTICE_PLAN.md)：两路8192完整库并行，固定639条hard增加练习，兼顾普通姿态质量和LAFAN保持；[P10协议](configs/next_stage_8k_hard_practice_protocol.json)、[P10启动词](docs/P10_CODEX_START_PROMPT.md)、[冻结hard名单](configs/p10_hard_motion_set.json)、[P9深读复核](docs/P9_REVIEW_20261108.md)。[已完成P9方案](docs/P9_CRITIC_AND_FULL_SCALE_PLAN.md)、[P8深读复核](docs/P8_REVIEW_20261107.md)。[已完成P8方案](docs/P8_STABILITY_AND_SCALE_PLAN.md)、[已完成P7方案](docs/P7_CONTINUATION_AND_FRESH_PLAN.md)、[已完成P6方案](docs/P6_POSITION_FEEDBACK_PLAN.md)、[历史复现记录](docs/REPRODUCTION_PLAN.md)。
- [来源锁](configs/sources.lock.json)：LAFAN1、机器人资产和 BeyondMimic 参数的确切版本。
- [运行配置](configs/lafan40.json)：论文规模的初始学习预算；[开发配置](configs/lafan40_development.json) 只缩短更新次数。
- [数据来源](data/sources.json)：原始数据入口；40 条动作的实际哈希、时长与质量记录见 `results/lafan1_g1_preparation/motion_manifest.json`。
- [环境记录](environment.json)：本机实际安装版本与准备检查。
- [official-src/](official-src/README.md)：官方来源与独立工作区说明，未将上游代码直接混入本仓库。
- `outputs/`、`checkpoints/`、`data/raw/`、`data/processed/`：执行产物位置，默认不进入 Git。

## 实施原则

采样、世界模型拟合与策略/Critic 更新交替进行；固定世界模型参数时保留经过其输入的梯度。P6已通过对照研究支持给Actor追加当前相对根位置3维；P7两任务均使用这一713维goal encoder输入（另有10×93历史观测，713并非总Actor输入）；P8两条LAFAN支完成H32/H16对照，结果支持保留H32；P9在同一H32父节点比较Critic累计存活加权，并同步推进修正完整库与LAFAN共同训练。论文未展开goal全部特征/坐标，这一输入是本项目有依据的实验，不将其冒充作者公开定义。完整动作回放、实际失败与耗时都保留；训练回报、完整片段评估和作者报道结果分别记录。

用户已授权 G1 的 LAFAN1 训练、完整评估和 PPO-Sim 对比，先把前期实现和运行打通。用户允许与主要使用 CPU 的 MPC/RL 作业共享 D57 GPU，不另设 12GB 显存限制；不修改其他项目环境或终止其任务。

## 运行与学习

**P3历史完成记录：20261102-h32-bce-s0。** 最新已完成训练阶段为顶部的O1；当前O2方案已发布但尚未启动，P12暂缓并保留计划。下文为独立实现历史，均不作为新启动指令。以下两组从同一B6000完整模型/优化器/sampler/RNG状态继续，各新增3000次联合更新，到9000。物理现场/replay重新建立，不声称逐样本轨迹完全一致。

| 版本 | 完整执行 | 完整时长归一化回报 | 平均完成比例 | 起身 | 跑步 |
|---|---:|---:|---:|---:|---:|
| 父B6000 | 13/40 | 0.409124 | 63.050% | 0/6 | 0/4 |
| **C0保留辅助BCE** | **29/40** | **0.615404** | **88.126%** | **3/6** | **3/4** |
| C1删除辅助BCE | 15/40 | 0.482603 | 68.228% | 1/6 | 2/4 |

C0保住父版本全部13条成功，新增16条完成，38/40条回报提高。C0在7000/8000/9000分别13/27/29条完成，回报0.403862/0.545387/0.615404，主线仍在学习。跑步未完成的一条已执行221.66/244.80秒；最顽固起身fallAndGetUp2_subject2仍在15.18秒失败。完整执行不等于精准跟踪，C0/C1共同存活区间XY误差仍为2.066/5.232m；coverage是附加诊断，不是论文成功率。这是P3当时的训练动作覆盖，彼时尚未达到论文回报；最新P6已超过LAFAN1的0.82参照，效率、大规模与实机范围仍另行区分。

原文Eq.(1)没有要求BCE对预测状态detach，k8/H32也是默认。P3不支持删除BCE作为修复；C0更好不等于其世界模型在全部失败窗口更准确。论文LAFAN的0.82作为效果参照；320000是表列训练长度，不要求机械跑满，也不把9000判为收敛。

**P4已完成：一个C0连续run，9000→18000。** 预计新增约9.7小时，训练阶段上限12小时；单个Codex交互窗口≤4小时，tmux跨窗口继续，不重启训练/replay/LR。保留H32、robot_root、目标710维、aux_bce和当前算法设置。每1000新增轮完整评估40条动作并先发布轻量结果，原始轨迹留服务器；必要视频按需复用评分轨迹。P4本段训练和正式评估已结束，实际状态与结果见本文顶部链接。

P4/P5/P6/P7/P8的训练、正式评估与关键发布均已完成。P6位置反馈将共同完整31动作的XY从A的2.0917m降到B的0.0640m；P7进一步表明多数动作质量提高与动态技能保持存在分化。P8已完成H16/H32对照与BONES40迁移。P8复核发现零存活想象后缀支配两次Critic巨额MSE，BONES筛选高度/名称定义需要修正，迁移后存在广泛LAFAN遗忘；P9按这些证据安排稳定性与完整库训练。

- [P3结果与发布清理](results/20261102-h32-bce-s0/summary.json)
- [逐动作/里程碑/真实失败窗口](results/20261102-h32-bce-s0/comparison.json)
- [正式训练区间统计](results/20261102-h32-bce-s0/training.json)
- [历史审阅与P4计划](docs/REPRODUCTION_PLAN.md#p4-next-stage)
- [P4机器可读协议](configs/next_stage_continuation_protocol.json)（不是train.py配置）
- [当前O2启动词](docs/O2_CODEX_START_PROMPT.md)、[O1历史完成交接](docs/O1_CODEX_START_PROMPT.md)
- [备选P12启动提示词](docs/P12_CODEX_START_PROMPT.md)
- [P4父版本C0-9000](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261102-h32-bce-s0-h32_aux_bce-i0009000)

P3已status=completed、unpublished=[]，记录删除496个明确实验文件、释放14,243,586,048字节（约14.24GB）。[最终Release](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261102-h32-bce-s0-final)已发布。以上是历史清理记录。当前P4已恢复所需工作输入；此后大产物默认留服务器，由用户备份和统一删除，助手不自动归档或清理，环境/源码/G1资产与工作树保留。

### 已完成阶段与历史记录

P2实际入口为 `bash scripts/run_goal_feedback_d57.sh 20261101-goal-feedback-s0`：先B后A，各seed 0从头初始化，最终均6000轮；每1000轮完整评估与发布。目标编码贯穿真实采样、想象每步、末端价值和评估，不计算数据文件摘要。P2的运行协议保留在 [next_stage_correction_protocol.json](configs/next_stage_correction_protocol.json)，当前新增任务以顶部O2方案和启动词为准。

2026-11-01：首轮 `20261031-learning-s0` 已在北京时间 01:25 正常完成：SuperMimic 与 PPO-Sim 各 3 h，均完成 40 条动作的完整评估。SuperMimic 最终第 2874 轮为 0/40 完整执行、平均 3.052 s、完成比例 1.351%、归一化回报 0.003570；PPO-Sim 最终第 5614 轮为 12/40、109.566 s、46.912%、0.213527。PPO-Sim 第 5000 轮为 16/40，优于最终版本，所有节点保留。完整执行按原高度/倾斜终止规则判定，并不代表精确轨迹跟踪；PPO 最终完成的 12 条动作仍有 1.41–11.05 m 的逐动作平均根位置误差。

最终权重与诊断：[SuperMimic 2874](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261031-learning-s0-supermimic-i0002874)、[PPO-Sim 5614](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261031-learning-s0-ppo_sim-i0005614)。完整逐动作结果、各轮指标及恢复历史见 [本轮汇总](results/20261031-learning-s0/summary.json)。原始日志已归档，恢复后的相对路径为 `outputs/campaigns/20261031-learning-s0.log`。

终止处理对照 `20261101-termination-s0` 已于北京时间 2026-11-01 15:52 完成，两组各 3 h、seed 0、相同初始化、H=32；配置只相差 `imagination_termination`。学习型组最终第 2678 轮为 0/40 完整执行、平均 3.299 s、完成比例 1.5263%、归一化回报 0.004678；解析平滑组最终第 2793 轮为 20/40、159.15 s、68.7140%、0.278330。40 条动作的执行时间和回报均提高。两组最终权重、完整评估与诊断均已发布，见 [本轮汇总](results/20261101-termination-s0/summary.json) 和 [逐动作及机制对照](results/20261101-termination-s0/comparison.json)。

该结果支持解析平滑终止在本次同预算单 seed 实现中改善实际控制；解析组多完成 115 轮更新，且共享 GPU 负载不同，因此不将墙钟效率或所有改善单独归因于世界模型。完成的 20 条动作仍有 1.11–7.59 m 的逐动作平均根位置误差，跌倒起身仍为 0/6。原终止网络的 BCE 训练保留，仅替换想象 Actor/Critic 使用的概率。协议、诊断解释和限制见 [复现计划](docs/REPRODUCTION_PLAN.md) 与 [机器可读协议](configs/termination_ablation_protocol.json)。按用户要求，当前先分析结果，没有启动下一轮实验。

固定权重录像已发布：[五类动作总览及完整视频](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261101-termination-s0-videos-v1)。左侧是运动学参考，中间为学习型终止，右侧为解析平滑终止；失败后画面冻结并保留时间、根位置/关节误差及全局 XY 轨迹。录像对应一次独立重放，结果为 0/40 与 19/40，原始评估 0/40 与 20/40 保留；[录像数据与分项统计](results/20261101-termination-s0/videos) 独立保存。

用户授权的存储清理已于北京时间 2026-11-01 20:31 正常结束。18 个归档分卷及 5 个恢复元数据资产均完成 GitHub 大小/SHA256 校验；119 个检查点全部覆盖，其中 104 个在归档中、15 个复用已发布权重，并已从 GitHub 实际取回一个检查点、严格载入模型和优化器。清理窗口实测回收 49.85 GB，扣除本次生成的 18.29 GB 临时分卷后，原项目净释放约 31.56 GB。D57 本项目只剩约 40.7 MiB 的轻量源码和结果。π0、π0.5、MPC/RL 及共享 uv 缓存不在删除范围，保护文件与根目录核对未变。详见 [最终核验](results/storage_cleanup/20261101/final_verification.json)；动作输入和环境按固定来源、原始 manifest 与依赖锁重建。没有安排新的算法对照。

上述空间数字记录的是 20:31 清理完成时的状态。随后根据用户反馈纠正了清理范围：已恢复约 7.57 GB 的常驻开发环境和轻量机器人资产，源码主目录同步到最新版本，原未提交改动保存在 Git stash。今后清理数据默认保留源码、环境、依赖锁、机器人资产与工作树；已结束的 20261101 清理入口再次运行会直接返回，不会删除恢复后的环境。

```bash
# 历史会话示例：任务已结束，实例重启后旧会话不再存在。
ssh autodl-d57
tmux attach -t sm-g1-lafan40
# 退出查看而保留任务：Ctrl-b，然后 d
```

终止单因素对照入口（在独立 tmux 中调用）：

```bash
bash scripts/run_termination_ablation_d57.sh 20261101-termination-s0
```

两组均每轮原子保存完整检查点，保留最近 20 轮和所有 1000 轮节点；每 1000 轮自动完整评估、诊断并发布。每组预算结束后还会发布不满 1000 整数节点的最终检查点与诊断，自动合并完整实验汇总到运行索引。

```bash
# 数据准备（下载只发生在 D57；保存原始动作，不静默剔除困难片段）
bash scripts/prepare_d57.sh

# 历史前期入口，已完成；P2 v2 不再重复运行
# bash scripts/validate_preparation_d57.sh

# 独立 tmux 中运行真实短程学习和每种方法的 40 条完整评估
tmux new-session -d -s sm-g1-learning 'cd /root/autodl-tmp/robot-repro/supermimic && bash scripts/run_development_d57.sh 20261031-r1'
tmux attach -t sm-g1-learning

# 完整预算入口（执行状态以运行索引为准）
python scripts/train.py --method supermimic --config configs/lafan40.json --run lafan40-sm-seed0
python scripts/evaluate.py outputs/runs/lafan40-sm-seed0/checkpoint_latest.pt
python scripts/train.py --method ppo_sim --config configs/lafan40.json --run lafan40-ppo-seed0
python scripts/evaluate.py outputs/runs/lafan40-ppo-seed0/checkpoint_latest.pt
```

`metrics.jsonl` 保存每次真实更新的模型误差、终止 BCE、策略梯度、Critic 误差、仿真采样量与分阶段耗时。`evaluation.json` 保存每条动作的完成度、回报和第一失败原因，失败后的剩余时长进入归一化分母。`failure.json` 保留实现或数值失败。检查点包含模型、优化器与采样权重；恢复时重新预热 replay，不声称逐比特接续物理状态。

用户在 2026-10-31 要求更密集的保存和推送：现在每轮原子保存完整模型/优化器检查点，保留最近 20 轮、初始版本和每个 1000 轮节点。编号文件不可覆盖，`checkpoint_latest.pt` 指向最近版本。检查点约数百 MB，滚动保留避免逐轮长期累积占满共享数据盘；回退到较旧版本时使用新的 run 名称。

P5沿用每1000新增轮完整评估40条动作，先推完整评分JSON、每1000轮关键训练统计和结论；完整逐轮日志留服务器。原始评分轨迹保存于服务器，必要视频按需生成。权重、完整视频、原始数组和大日志默认不上传，也不自动做阶段清理；用户定期导出备份并统一删除。训练器原有最近20轮滚动保留规则照旧，里程碑、最终与续训所需权重保留。在现有索引记录服务器产物路径和用途，不新增归档系统。2026-11-03 22:15已将实际publish_checkpoint.py与finish_c0_continuation.py切换为轻量Git发布。P4训练PID149031随后已于18000轮正常结束。P4从14000节点起不创建Release、不打包或上传大产物，收尾不批量渲染、不删除阶段或输入副本；P5/P6/P7的紧凑统计及多run发布适配已完成；P8三路与40h子集评估适配已完成；P9的Critic候选、修正完整库/混合来源与有界参考窗口适配及三路训练均已完成；P10扩大batch、hard reset与评分组批及P11高度对照均已完成；P12窗口/offset统计及薄调度适配尚未实施。

需要查看策略时，优先使用已发布节点的正式评估和视频；本轮每1000轮自动完成一次全40评估，不另开旧版本重复回放。

学习顺序：先理解参考动画与动态控制的区别；再观察世界模型是否提升真实仿真表现；最后在相同动作、任务、网络与评估下比较 PPO-Sim。八次开发迭代不能作为两种方法优劣的证据。

P3 v2历史执行入口（已完成，不重复运行）：`bash scripts/run_tracking_continuation_d57.sh 20261102-h32-bce-s0`。独立源码工作树 `/root/autodl-tmp/robot-repro/supermimic-p3-h32` 复用主项目原位 `.venv` 和 G1 资产；主目录的 P2 未提交文件保持原位。实际配置为 `configs/lafan40_h32_state_only.json` 和 `configs/lafan40_h32_aux_bce.json`。从同一 B6000 恢复全部网络、优化器、sampler 和已保存的 Torch/CUDA RNG；NumPy 保持 seed 0。恢复完成后重新计本段预算，6001 轮接续全局 LR；父版本不重复评估。保留原 70 维逐维 mean，C1 的 BCE 记录为 null（未计算），不记作零误差。

P3 v2已完成两组9000轮训练、全部完整评估、发布和精确副本清理。历史tmux为sm-p3-h32-bce-s0，实际执行记录保存在results/index.json的对应campaign；P4/P5/P6/P7/P8/P9/P10/P11及O1亦已完成；当前新增任务为顶部O2方案，不重复启动旧阶段。

P3 v2 实际阶段结果：h32_aux_bce 第9000轮，29/40，归一化回报0.61540441，新增3000轮/3.225h；h32_state_only 第9000轮，15/40，归一化回报0.48260317，新增3000轮/3.236h。结果和实际失败窗口见 results/20261102-h32-bce-s0/summary.json、comparison.json；该阶段不能作为充分收敛证据。

P4最终判断：18000轮达到本阶段最高完整回报0.706754，较9000提高14.84%，完整执行由29增至32；15000–17000的回撤后出现恢复，不能据此宣布收敛或持续停滞。保留C0-18000作为后续续训起点，保留全部里程碑用于检查动作保持。起身成功集合仍会变化，且真实失败尾窗存在状态预测/解析终止失配；若继续研究，优先沿同配置观察这些能力能否稳定保持。本段已结束，没有自动追加训练预算或新分支。 详细逐动作变化与三条真实起身失败尾窗见 [P4结论](docs/REPRODUCTION_PLAN.md#p4-next-stage)。



