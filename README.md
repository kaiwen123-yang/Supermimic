# SuperMimic 独立复现

本仓库用于依据论文独立实现 **SuperMimic: Scaling Humanoid Whole-Body Control with One Differentiable World Model**。当前完成仓库、隔离依赖、论文参数和实施安排的初始化；**算法代码尚未实现，尚未训练或评测**。

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
- [执行准备](docs/REPRODUCTION_PLAN.md)：实现范围、待明确的定义、对照与评估方式。
- [数据来源](data/sources.json)：原始 LAFAN1、BONES-SEED 与权限/版本状态；尚未下载训练数据。
- [环境记录](environment.json)：本机实际安装版本与准备检查。
- `official-src/`：官方源码预留位置，未放入第三方复现代码。
- `outputs/`、`checkpoints/`、`data/raw/`、`data/processed/`：执行产物位置，默认不进入 Git。

## 实施原则

采样、世界模型拟合与策略/Critic 更新交替进行；固定世界模型参数时保留经过其输入的梯度。Actor 的输入遵守论文观测边界。完整动作回放、实际失败与耗时都保留；训练回报、完整片段评估和作者报道结果分别记录。

本轮仅初始化和准备，不启动训练、仿真、基准测试或实机控制。后续实施按用户的下一条任务推进。
