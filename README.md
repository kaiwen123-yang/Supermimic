# SuperMimic 独立复现

本仓库用于以学习为目的，依据论文独立实现 **SuperMimic: Scaling Humanoid Whole-Body Control with One Differentiable World Model**。当前已接入固定版本的 LAFAN1 40 条完整动作、G1 / MuJoCo Warp、可微运动学、SuperMimic 核心训练循环、PPO-Sim 和完整动作评估。实际运行结果见 `results/index.json`；源码实现、短程更新和复现成绩分别记录。

- 论文：[arXiv:2610.28480v1](https://arxiv.org/abs/2610.28480v1)
- 作者项目：[supermimic.github.io](https://supermimic.github.io/)
- 当前路线：G1 + MuJoCo Warp，先对齐 LAFAN1 实验，再按实际结果决定是否扩展 BONES-SEED。
- 本仓库属于独立复现，不是作者官方代码。2026-10-31 核对作者项目页，未取得官方训练仓库；没有导入社区复现实现。

## D57 环境

SSH 别名 `autodl-d57`；项目目录 `/root/autodl-tmp/robot-repro/supermimic`。GPU 为单张 RTX PRO 6000 96GB。

```bash
cd /root/autodl-tmp/robot-repro/supermimic
source activate.sh
```

重建依赖：
```bash
bash scripts/setup_d57.sh
```

`pyproject.toml` / `uv.lock` 固定本机准备环境，Python 3.11，Torch 2.7.1+cu128，MuJoCo / MuJoCo Warp 3.17.0。这些是**本机准备版本**，作者的完整软件锁未公开；确定机器人模型和仿真实现时需记录版本选择。

每套项目使用独立 `.venv` 和 pip，不继承 Conda base、MPC-RL 或 π 系列的包。源码、模型、数据、输出和缓存分别存放。GPU 显存与算力仍属于共享硬件，启动计算前核对实际任务安排。

## 现有内容

- [论文配置](configs/paper_reference.toml)：按论文标注来源的算法/网络/训练参数，不是已经可执行的训练配置。
- [执行准备](docs/REPRODUCTION_PLAN.md)：实现选择、对照、评估和学习问题。
- [来源锁](configs/sources.lock.json)：LAFAN1、机器人资产和 BeyondMimic 参数的确切版本。
- [运行配置](configs/lafan40.json)：论文规模的初始学习预算；[开发配置](configs/lafan40_development.json) 只缩短更新次数。
- [数据来源](data/sources.json)：原始数据入口；40 条动作的实际哈希、时长与质量记录见 `results/lafan1_g1_preparation/motion_manifest.json`。
- [环境记录](environment.json)：本机实际安装版本与准备检查。
- `official-src/`：官方源码预留位置，未放入第三方复现代码。
- `outputs/`、`checkpoints/`、`data/raw/`、`data/processed/`：执行产物位置，默认不进入 Git。

## 实施原则

采样、世界模型拟合与策略/Critic 更新交替进行；固定世界模型参数时保留经过其输入的梯度。Actor 的输入遵守论文观测边界。完整动作回放、实际失败与耗时都保留；训练回报、完整片段评估和作者报道结果分别记录。

用户已授权 G1 的 LAFAN1 训练、完整评估和 PPO-Sim 对比，先把前期实现和运行打通。用户允许与主要使用 CPU 的 MPC/RL 作业共享 D57 GPU，不另设 12GB 显存限制；不修改其他项目环境或终止其任务。

## 运行与学习

2026-10-31：40 条动作准备完成，两轮短程开发训练和完整动作评估已经执行。首轮持续学习在 D57 的 `sm-g1-lafan40` tmux 会话中运行，tag 为 `20261031-learning-s0`；先 SuperMimic 3 h，离线评估保留的检查点，再 PPO-Sim 3 h 和完整评估。Git 中的运行索引是标注时间的快照，最新日志位于服务器 `outputs/campaigns/20261031-learning-s0.log`。任务结束后自动在 D57 生成紧凑结果，尚未产生的结果不预先发布。

```bash
ssh autodl-d57
tmux attach -t sm-g1-lafan40
# 退出查看而保留任务：Ctrl-b，然后 d
```

```bash
# 数据准备（下载只发生在 D57；保存原始动作，不静默剔除困难片段）
bash scripts/prepare_d57.sh

# 数值核对与未学习的参考 PD 诊断
bash scripts/validate_preparation_d57.sh

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

每 1000 轮自动建立独立发布 tmux：固定该版本，完成全部 40 条动作评估；SuperMimic 另外做 120 个确定性起点的 1/8/16/32 步真实仿真—模型对照。权重和复现元数据进入 GitHub Release，逐动作结果与指标进入 Git；逐个核对 GitHub 返回的资产大小和 SHA256 后发布。上传失败会保留失败记录，训练继续，已发布节点不被覆盖。运行索引区分“训练仍在进行，但已有阶段评估”和“训练预算及最终评估完成”。

需要查看最新策略时，可在训练期间运行以下命令。评估会固定一次具体版本，即使 latest 继续变化或旧版本被滚动清理，结果和校验和仍对应同一组权重。

```bash
python scripts/evaluate.py outputs/runs/20261031-learning-s0-supermimic/checkpoint_latest.pt
```

学习顺序：先理解参考动画与动态控制的区别；再观察世界模型是否提升真实仿真表现；最后在相同动作、任务、网络与评估下比较 PPO-Sim。八次开发迭代不能作为两种方法优劣的证据。
