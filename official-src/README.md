# 官方来源与独立工作区

## 当前状态：O1官方LAFAN40首段已完成

本次复核依据用户仓库2b44fa32587e1a68be8b9d4de61485cd267e29c8。实际运行来源为：

- 官方仓库：[HybridRobotics/supermimic](https://github.com/HybridRobotics/supermimic)，固定[abc124c1bd5976341034668af3d12c087f2f1f55](https://github.com/HybridRobotics/supermimic/tree/abc124c1bd5976341034668af3d12c087f2f1f55)。
- 作者研究依赖：[HybridRobotics/mjlab_research](https://github.com/HybridRobotics/mjlab_research)，固定[dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd](https://github.com/HybridRobotics/mjlab_research/tree/dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd)。
- 两仓库均为Apache-2.0许可；官方当前README明确指定上述研究库。

D57工作区 /root/autodl-tmp/robot-repro/supermimic-official-workspace 的两源码、40条转换数据和独立环境均已就绪，本段训练与正式评分已经结束。3h节点R=0.8588231143475866、39/40完整；final节点R=0.8744398924149845、40/40完整。累计训练11296.659658696502秒，stop_reason=formal_return_target_reached。

当前结论见[O1完整复核](../docs/O1_REVIEW_20261111.md)、[派生结果](../results/20261111-o1-official-lafan40-s0/review_20261111.json)和[原始汇总](../results/20261111-o1-official-lafan40-s0/summary.json)，实际接入与运行过程见[O1正式接入说明](../docs/O1_OFFICIAL_RUN_20261111.md)。不重跑本段、不补足原12h上限，也不自动启动BONES或P12。

## 初始来源记录

2026-11-11初始源码比较固定在5efbf114e11f725c31d83e217be987c13c0e4ce2，当时README指定的kevinzakka/mjlab_research不可访问。作者随后将README依赖地址改为HybridRobotics/mjlab_research并公开对应源码；**旧地址404不是当前阻塞。**

直接比较5efbf114与abc124c两个快照，变化仅在README、项目描述与CI依赖地址，学习源码未变。旧readiness.json和13:42接续记录仅描述依赖公开前的历史状态；[Issue #1](https://github.com/HybridRobotics/supermimic/issues/1)的旧报错不能覆盖已取得新官方依赖并完成训练的事实。

本目录仅保留来源说明，没有将上游代码复制进独立实现，也没有导入社区复现代码。旧实现与已有成果保留。

阅读[完整比较报告](../docs/OFFICIAL_COMPARISON_20261111.md)、[O1初始执行计划及完成状态](../docs/O1_OFFICIAL_REPRODUCTION_PLAN.md)和[来源清单](../configs/official_source_inventory_20261111.json)。当前公开main与论文原始主配置继续分别标注。

