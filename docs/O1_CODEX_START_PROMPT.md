# O1 Codex 完成交接：首段已达标

2026-11-11：官方LAFAN40首段已完成训练、两份正式评分和轻量发布。本文件原先用于启动O1；**原启动任务已经执行完毕，不再作为重复训练指令**。原文可从[结果复核前的历史版本](https://github.com/kaiwen123-yang/Supermimic/blob/2b44fa32587e1a68be8b9d4de61485cd267e29c8/docs/O1_CODEX_START_PROMPT.md)溯源。

## 当前结果

| 节点 | 全40平均R | 完整数 | 训练时间 |
|---|---:|---:|---:|
| hour_03 | 0.85882311 | 39/40 | 约3h |
| final | 0.87443989 | 40/40 | 约3h8m17s |

seed0从零初始化；3h正式达标后训练正常停止，final随后评分完成。原6h/12h节点无需补跑。当前完整状态见[summary.json](../results/20261111-o1-official-lafan40-s0/summary.json)，效果与边界见[O1完成复核](O1_REVIEW_20261111.md)，环境及实际执行细节见[正式接入记录](O1_OFFICIAL_RUN_20261111.md)。

## 后续接续上下文

可把以下内容交给能访问D57的后续会话，作为已完成状态和下一阶段设计背景；它本身不启动新的训练段。

```text
请先读取AGENTS.md、docs/O1_REVIEW_20261111.md、docs/O1_OFFICIAL_RUN_20261111.md和results/20261111-o1-official-lafan40-s0/summary.json。O1已completed：首个3h节点R=.85882311、39/40；final R=.87443989、40/40，累计训练约3h8m17s，因formal_return_target_reached停止。latest_training的evaluation_pending是退出时历史快照，final已经完成。不要重复启动sm-o1-official-lafan40-s0、补6h/12h或重评已有节点。

当前学习主线继续采用官方代码。实际源码为HybridRobotics/supermimic@abc124c1bd5976341034668af3d12c087f2f1f55、HybridRobotics/mjlab_research@dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd；旧kevinzakka地址404不是当前阻塞。D57官方工作区为/root/autodl-tmp/robot-repro/supermimic-official-workspace，两份相邻源码、独立Python3.13环境和LAFAN40数据已可复用。不要重新安装、下载、retarget或覆盖其他项目环境。

保留O1 GenCoord/proprio/history10基线、3h/final权重与成绩，保留独立实现P6—P11历史结论。O1全40的平均XY误差.765250m、9条>=1m，是后续质量研究问题，不撤销LAFAN指标达标；不先追加XYZ、BCE、hard配额、P11高度修正或重开P12。

下一阶段重点准备官方BONES具体方案。已保留的P9连续store为/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9，manifest及六数组均保留。历史逐clip NPZ已按另一项明确授权清理，不再依赖旧NPZ glob，也不因格式适配就恢复全部H盘归档。官方MotionLoader已经支持六字段packed目录，可沿O1关节顺序与根角速度坐标映射，从现有qpos/qvel分块生成；不另写训练loader、不重新准备原始数据。packed参考默认整体搬到device，约12.624GiB仅为BONES静态参考，不当总训练显存。

项目BONES为130394条，作者129514条的精确筛选成员未取得；不要删880条凑数，也不要将旧独立实现全BONES结果记成官方结果。具体下一段需明确数据范围、从零或权重warm-start、实际预算、正式全库评分与LAFAN保持口径。O1只保存网络/normalizer/config/计数，没有optimizer/replay/sampler/RNG的full resume；若使用其权重，不称完整恢复。本交接只提供已完成事实及下一阶段设计依据，不自动开始新的训练预算。

继续轻量Git发布：实际代码/config、全部逐clip标量、关键统计和结论进Git；大模型/日志/轨迹留服务器。保留原件和其他任务，遵循禁止无关测试、benchmark、恢复演练、额外扫描及自动归档清理的约定。
```

