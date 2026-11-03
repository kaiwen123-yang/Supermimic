# SuperMimic 独立复现

> **2026-11-03产物约定更新：** 先推代码、配置、逐回合/逐动作JSON、训练JSON/JSONL与结论并继续研究。大checkpoint、完整视频、原始数组/轨迹和数据缓存默认不上传GitHub，由用户从服务器导出到自己的存储盘备份并统一删除；取消旧的阶段自动清理。当前P4训练保持运行。[完整约定](docs/REPRODUCTION_PLAN.md#p4-next-stage)与[接管提示词](docs/NEXT_STAGE_START_PROMPT.md)。

> **P4已于北京时间2026-11-03 16:36:41开始新训练阶段。** 单个C0 run从9000连续推进至最多18000轮/12小时，保留辅助BCE；一次64步replay预热后完整执行真实采样→WM→Actor/Critic。当前仍在训练，尚无P4正式评估成绩。[运行记录](results/20261103-c0-continuation-s0/summary.json)。独立tmux `sm-p4-c0-continuation-s0` 跨聊天窗口持续运行，不重启训练。

本仓库用于以学习为目的，依据论文独立实现 **SuperMimic: Scaling Humanoid Whole-Body Control with One Differentiable World Model**。当前已接入固定版本的 LAFAN1 40 条完整动作、G1 / MuJoCo Warp、可微运动学、SuperMimic 核心训练循环、PPO-Sim 和完整动作评估。实际运行结果见 `results/index.json`；源码实现、短程更新和复现成绩分别记录。

- 论文：[arXiv:2610.28480v1](https://arxiv.org/abs/2610.28480v1)
- 作者项目：[supermimic.github.io](https://supermimic.github.io/)
- 当前路线：G1 + MuJoCo Warp，先对齐 LAFAN1 实验，再按实际结果决定是否扩展 BONES-SEED。
- 本仓库属于独立复现，不是作者官方代码。2026-11-03重新核对作者公开材料，仍未取得官方训练仓库；没有导入社区复现实现。

## D57 环境

SSH 别名 `autodl-d57`；项目目录 `/root/autodl-tmp/robot-repro/supermimic`。GPU 为单张 RTX PRO 6000 96GB。

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

`pyproject.toml` / `uv.lock` 固定本机准备环境，Python 3.11，Torch 2.7.1+cu128，MuJoCo / MuJoCo Warp 3.17.0。这些是**本机准备版本**，作者的完整软件锁未公开；确定机器人模型和仿真实现时需记录版本选择。

每套项目使用独立 `.venv` 和 pip，不继承 Conda base、MPC-RL 或 π 系列的包。源码、模型、数据、输出和缓存分别存放。GPU 显存与算力仍属于共享硬件，启动计算前核对实际任务安排。

## 现有内容

- [论文配置](configs/paper_reference.toml)：按论文标注来源的算法/网络/训练参数，不是已经可执行的训练配置。
- [复现记录与当前计划](docs/REPRODUCTION_PLAN.md#p4-next-stage)：P3实际结果、原文复核与P4连续续训。
- [来源锁](configs/sources.lock.json)：LAFAN1、机器人资产和 BeyondMimic 参数的确切版本。
- [运行配置](configs/lafan40.json)：论文规模的初始学习预算；[开发配置](configs/lafan40_development.json) 只缩短更新次数。
- [数据来源](data/sources.json)：原始数据入口；40 条动作的实际哈希、时长与质量记录见 `results/lafan1_g1_preparation/motion_manifest.json`。
- [环境记录](environment.json)：本机实际安装版本与准备检查。
- `official-src/`：官方源码预留位置，未放入第三方复现代码。
- `outputs/`、`checkpoints/`、`data/raw/`、`data/processed/`：执行产物位置，默认不进入 Git。

## 实施原则

采样、世界模型拟合与策略/Critic 更新交替进行；固定世界模型参数时保留经过其输入的梯度。P4保持当前710维目标输入和H32；论文未展开goal全部特征/坐标，当前实现选择明确记录，不将额外状态输入冒充作者公开定义。完整动作回放、实际失败与耗时都保留；训练回报、完整片段评估和作者报道结果分别记录。

用户已授权 G1 的 LAFAN1 训练、完整评估和 PPO-Sim 对比，先把前期实现和运行打通。用户允许与主要使用 CPU 的 MPC/RL 作业共享 D57 GPU，不另设 12GB 显存限制；不修改其他项目环境或终止其任务。

## 运行与学习

**最新已完成训练：P3 20261102-h32-bce-s0。** 两组从同一B6000完整模型/优化器/sampler/RNG状态继续，各新增3000次联合更新，到9000。物理现场/replay重新建立，不声称逐样本轨迹完全一致。

| 版本 | 完整执行 | 完整时长归一化回报 | 平均完成比例 | 起身 | 跑步 |
|---|---:|---:|---:|---:|---:|
| 父B6000 | 13/40 | 0.409124 | 63.050% | 0/6 | 0/4 |
| **C0保留辅助BCE** | **29/40** | **0.615404** | **88.126%** | **3/6** | **3/4** |
| C1删除辅助BCE | 15/40 | 0.482603 | 68.228% | 1/6 | 2/4 |

C0保住父版本全部13条成功，新增16条完成，38/40条回报提高。C0在7000/8000/9000分别13/27/29条完成，回报0.403862/0.545387/0.615404，主线仍在学习。跑步未完成的一条已执行221.66/244.80秒；最顽固起身fallAndGetUp2_subject2仍在15.18秒失败。完整执行不等于精准跟踪，C0/C1共同存活区间XY误差仍为2.066/5.232m；coverage是附加诊断，不是论文成功率。当前是训练动作覆盖，尚未复现论文最终效果、效率、大规模与实机结果。

原文Eq.(1)没有要求BCE对预测状态detach，k8/H32也是默认。P3不支持删除BCE作为修复；C0更好不等于其世界模型在全部失败窗口更准确。论文LAFAN的0.82作为效果参照；320000是表列训练长度，不要求机械跑满，也不把9000判为收敛。

**下一步P4：一个C0连续run，9000→18000。** 预计新增约9.7小时，训练阶段上限12小时；单个Codex交互窗口≤4小时，tmux跨窗口继续，不重启训练/replay/LR。保留H32、robot_root、目标710维、aux_bce和当前算法设置。每1000新增轮完整评估40条动作并先发布轻量结果，原始轨迹留服务器；必要视频按需复用评分轨迹。P4已正式启动，当前训练进行中，实际进度见顶部运行记录。

实际需要的实现工作是适配旧两组启动/收尾脚本到单run、正确更新最终发布和评估状态；没有发现需先改的确定算法错误。暂不新增H16/XYZ、BCE权重或state loss归约对照。

- [P3结果与发布清理](results/20261102-h32-bce-s0/summary.json)
- [逐动作/里程碑/真实失败窗口](results/20261102-h32-bce-s0/comparison.json)
- [正式训练区间统计](results/20261102-h32-bce-s0/training.json)
- [完整审阅与P4计划](docs/REPRODUCTION_PLAN.md#p4-next-stage)
- [P4机器可读协议](configs/next_stage_continuation_protocol.json)（不是train.py配置）
- [P4启动提示词](docs/NEXT_STAGE_START_PROMPT.md)
- [P4父版本C0-9000](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261102-h32-bce-s0-h32_aux_bce-i0009000)

P3已status=completed、unpublished=[]，记录删除496个明确实验文件、释放14,243,586,048字节（约14.24GB）。[最终Release](https://github.com/kaiwen123-yang/Supermimic/releases/tag/sm-20261102-h32-bce-s0-final)已发布。以上是历史清理记录。当前P4已恢复所需工作输入；此后大产物默认留服务器，由用户备份和统一删除，助手不自动归档或清理，环境/源码/G1资产与工作树保留。

### 已完成阶段与历史记录

P2实际入口为 `bash scripts/run_goal_feedback_d57.sh 20261101-goal-feedback-s0`：先B后A，各seed 0从头初始化，最终均6000轮；每1000轮完整评估与发布。目标编码贯穿真实采样、想象每步、末端价值和评估，不计算数据文件摘要。P2的运行协议保留在 [next_stage_correction_protocol.json](configs/next_stage_correction_protocol.json)，当前新增任务以P4协议为准。

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

P4沿用每1000新增轮完整评估40条动作，先推逐动作JSON、训练JSON/JSONL和结论。原始评分轨迹保存于服务器，必要视频按需生成。权重、完整视频、原始数组和大日志默认不上传，也不自动做阶段清理；用户定期导出备份并统一删除。训练器原有最近20轮滚动保留规则照旧，里程碑、最终与续训所需权重保留。在现有索引记录服务器产物路径和用途，不新增归档系统。当前运行中的旧发布/收尾脚本需由Codex接入新策略，文档更新不等于服务器进程已切换；接入时不重启正常训练或评估。

需要查看策略时，优先使用已发布节点的正式评估和视频；本轮每1000轮自动完成一次全40评估，不另开旧版本重复回放。

学习顺序：先理解参考动画与动态控制的区别；再观察世界模型是否提升真实仿真表现；最后在相同动作、任务、网络与评估下比较 PPO-Sim。八次开发迭代不能作为两种方法优劣的证据。

P3 v2历史执行入口（已完成，不重复运行）：`bash scripts/run_tracking_continuation_d57.sh 20261102-h32-bce-s0`。独立源码工作树 `/root/autodl-tmp/robot-repro/supermimic-p3-h32` 复用主项目原位 `.venv` 和 G1 资产；主目录的 P2 未提交文件保持原位。实际配置为 `configs/lafan40_h32_state_only.json` 和 `configs/lafan40_h32_aux_bce.json`。从同一 B6000 恢复全部网络、优化器、sampler 和已保存的 Torch/CUDA RNG；NumPy 保持 seed 0。恢复完成后重新计本段预算，6001 轮接续全局 LR；父版本不重复评估。保留原 70 维逐维 mean，C1 的 BCE 记录为 null（未计算），不记作零误差。

P3 v2已完成两组9000轮训练、全部完整评估、发布和精确副本清理。历史tmux为sm-p3-h32-bce-s0，实际执行记录保存在results/index.json的对应campaign；当前P4已启动，不重复启动。

P3 v2 实际阶段结果：h32_aux_bce 第9000轮，29/40，归一化回报0.61540441，新增3000轮/3.225h；h32_state_only 第9000轮，15/40，归一化回报0.48260317，新增3000轮/3.236h。结果和实际失败窗口见 results/20261102-h32-bce-s0/summary.json、comparison.json；该阶段不能作为充分收敛证据。
