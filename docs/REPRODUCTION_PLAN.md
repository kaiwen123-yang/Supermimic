# 实施准备

## 当前范围

独立实现 SuperMimic 的完整仿真学习循环，并以可核查的动作跟踪结果评价。当前只完成环境与仓库准备，训练、数据下载和算法实现均未执行。论文固定为 arXiv:2610.28480v1（2026-10-20），现有提取参数见 configs/paper_reference.toml。

## 第一阶段问题与证据

研究问题：在相同 G1 仿真、动作数据和评估条件下，通过学习到的可微动力学更新策略，能否提高真实仿真中的动作跟踪表现与学习效率？

第一阶段目标是对齐论文 LAFAN1 实验（40 clips / 2.45 h），但需先确认具体动作名单和 G1 重定向版本。原始 LAFAN1 含更多 BVH 序列，不能任取 40 条后声称数据完全一致。先从少量真实完整动作定位实现问题，随后执行固定动作集；不以短前缀或单个成功视频代表完成。

## 核心实现

1. G1 物理执行、参考动作时序、真实 transition 与 episode 边界。
2. replay buffer 的连续窗口；存储实际执行的带噪动作、状态与 episode sim context。
3. k-step autoregressive world-model 拟合。
4. H-step imagined rollout，Actor 的 BPTT 梯度和软生存权重；更新 Actor 时冻结世界模型权重并保留对输入的导数。
5. imagined-transition GAE targets 与 Critic 更新。
6. 论文的 return-based reset sampling；按同一调度交替采样、模型学习与策略学习。
7. 完整 motion 的固定策略评估、视频、失败分类和分项耗时。

这些模块当前未实现，不创建伪造训练入口或空“成功”结果。

## 实现前需要明确的定义

- 状态向量 s 的字段、坐标系和归一化；goal 的具体字段与参考坐标系。
- G1 MJCF/URDF 的确切版本、关节顺序、默认姿态、动作缩放与 PD gains。论文采用 BeyondMimic 定义，不能仅依据相同机器人名称认定等价。
- reward / observation / termination heads 在所复现实现中采用解析还是学习形式；论文正文允许两种形式，需要明确实际选择。
- update-to-data ratio=0.4 的具体调度计数口径。
- LAFAN1 的动作名单、重定向与重采样版本；BONES-SEED 的版本和过滤名单。
- 原论文未公开完整软件锁。本机已装 MuJoCo Warp 的版本属于准备配置，不作为作者版本声明。

以上选择会改变实验结果，应落在配置中。记录实际差异，不用兼容层或默认回退掩盖差异。

## 对照与评价

- 方法对照：同一环境、数据、观测、奖励、终止和评估协议下的 PPO-Sim。
- 机制对照按实现进展选择 Critic / imagination horizon 等论文相关项，不预先扩大组合。
- 主评价：从片段起点完整回放的归一化回报、失败次数与比例、跟踪误差。
- 工程记录：真实采样、世界模型、Actor/Critic 更新与评估的耗时；峰值显存。
- 学习曲线中的随机重置回报与完整片段回放结果分开。固定预算、seed 与 checkpoint 选择方式后再执行比较。
- 原论文大规模 benchmark 使用训练动作，报告覆盖能力时不称作对未见动作的泛化。

## 规模与资源

D57 单张 RTX PRO 6000 96GB。首轮真实执行测量吞吐、显存和资源占用后确定墙钟预算；H100 上的作者训练时间不直接承诺为 D57 时间。依赖隔离不能隔离共享 GPU 算力。

完成 LAFAN1 后，再根据结果决定是否扩展论文的 BONES-SEED 规模实验。完整数据下载须先核对存储与数据访问条件。用户尚未授权本初始化阶段启动这些计算。

## 来源

- [论文 v1](https://arxiv.org/abs/2610.28480v1)：§3、Appendix A–F，Algorithm A.1，Tables A.1–A.5。
- [作者项目](https://supermimic.github.io/)。
- [BONES-SEED](https://huggingface.co/datasets/bones-studio/seed)。
- [LAFAN1 原始数据](https://github.com/ubisoft/ubisoft-laforge-animation-dataset)。
