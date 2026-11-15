# O5 执行交接

更新时间：2026-11-16T00:37:28.784707+08:00。当前实际状态：**evaluating_lafan**。

- tmux：`sm-o5-optimizer-s0`。若已有活动进程或budget.json，只观察接续，不重复启动训练。
- 工作区：`/root/autodl-tmp/robot-repro/supermimic-official-workspace`；用户代码工作树：`/root/autodl-tmp/robot-repro/supermimic-o5-official-optimizer`。
- 官方源码：`supermimic-o5-optimizer`，基于abc124c；O3统计补丁一次，加O5优化器patch。研究库dd51a9f。
- 共同父O3 quarter32k；WM bundle、Actor、Critic、全部normalizer恢复；optimizer/replay/sampler/RNG新建。full_resume=false。
- A muon_wd0保留官方分组，仅Muon decay=0；B全Adam decay=0。三网络LR固定5e-5，每路4096环境。
- 每臂32000新增连续joint，合计64000；initial/8k/16k/32k/final，无小时截止、不按回报早停。
- 两训练child退出后串行全BONES再LAFAN评分及轻量发布；父/O4历史成绩复用。真实失败不自动重启。

| Arm | 当前训练状态 | 新增 / 32000 | 已观察退出 |
|---|---|---:|---|
| muon_wd0 | completed | 32000 | True |
| adam_wd0 | completed | 32000 | True |

合计：64000/64000。
- 驱动日志：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261115-o5-official-optimizer-s0/driver.log`。
- PID记录：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261115-o5-official-optimizer-s0/training_children.json`；真实退出：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261115-o5-official-optimizer-s0/training_children_exit.json`。
- 各run的`train_official.log`、`progress.json`和`nodes.json`保留实时与退出快照。
- 当前状态：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261115-o5-official-optimizer-s0/stage.json`；汇总：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/results/20261115-o5-official-optimizer-s0/summary.json`。
- 六历史节点的CPU范数读取在任一arm正常initial映射就绪后开始；不额外构建模型。

交接不重建replay、不重置LR、不停止后台。若仅评分或发布失败，定点接续该阶段，不重训或覆盖已有分数。
latest_training是子进程运行/退出快照；summary顶层与逐臂training字段为当前完成状态。
判断以32k和16k→32k全库R、共同完整R/XY/body orientation及父成功保持为主；历史O4不作为同步随机对照。
32k不等于132k长期稳定或完整论文配方复现。保留O3 quarter16k/32k、O4全部节点、O2/O1/P6及所有历史保护成果。
P12暂停，不自动开O6。大产物留D57；不Release、不tar、不自动归档或阶段清理。
