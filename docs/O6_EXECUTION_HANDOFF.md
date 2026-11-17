# O6 执行交接

更新时间：2026-11-17T08:06:08.851313+08:00；实际状态：**completed**。

- collection：320000/320000；实际joint：127997；真实transition：1310720000。
- tmux：`sm-o6-adam-cosine-s0`。已存在budget或活动进程时不重复启动训练。
- 工作区：`/root/autodl-tmp/robot-repro/supermimic-official-workspace`；用户工作树：`/root/autodl-tmp/robot-repro/supermimic-o6-official-adam-cosine`。
- 官方隔离源码：`supermimic-o6-adam-cosine`，abc124c＋O3统计patch＋O5优化器patch；研究库dd51a9f。
- 实际启动入口：`work/o6/run_d57.sh`；cwd/PYTHONPATH/import均为O6。复用既有Python和资产。
- seed0从零，parent=null，wandb_run_path=None；三网络与normalizer全新，无历史checkpoint加载。
- 全Adam WD0，初始2e-4；每次collection后、learner前对三网全部LR设备张量原位fill_；250k降至6e-6保持到320k。
- 320000 collection是完成条件；127997 joint仅为预期。无后台小时截止、无回报早停。
- 固定80k/160k/250k/320k只保存；训练child退出后依次全BONES和LAFAN评分、逐节点轻量发布。
- 同次正式评分保存固定四条时序和final最多8失败尾窗。历史分数复用，不重跑旧模型。
- driver日志：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261116-o6-official-adam-cosine-s0/driver.log`；训练日志：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o6-bones-adam-cosine-s0/train_official.log`。
- PID/退出：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261116-o6-official-adam-cosine-s0/training_child.json`、`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261116-o6-official-adam-cosine-s0/training_child_exit.json`。
- 实时训练：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o6-bones-adam-cosine-s0/progress.json`；节点：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o6-bones-adam-cosine-s0/nodes.json`。
- 阶段：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261116-o6-official-adam-cosine-s0/stage.json`；汇总：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/results/20261116-o6-official-adam-cosine-s0/summary.json`。

若仅评分失败，在确认没有活动评分后从run_d57.sh --start-at bones或lafan接续；已完成批次自动复用。
若仅发布失败，执行work/o6/publish_results.py --workspace WORKSPACE --label publication-retry；不得重训或重评。
真实训练异常不自动重启；checkpoint未保存完整optimizer/replay/sampler/RNG，不拼接成连续run。
保留O1/P6验收及O2/O3/O4/O5历史节点，P12暂停；O6收尾不自动开新训练。大产物留服务器，不Release/tar/本机归档或阶段清理。

## 2026-11-17 完成复核与后续计划

四节点训练、正式评分和轻量发布均完成；上面的失败接续说明仅供真实故障恢复，不是重新执行已完成阶段的指令。saved_nodes中的pending是保存时历史快照。

终点R=.953665488、39失败、XY5.180cm；250k为.953232182、36失败、5.229cm。最后70k修复11、丢失14，共同完整集合质量仍改善；monkey18仅完整1条，全部494长动作尾段小幅回撤。39个终点失败均在某个历史节点完成过。

完整复核：[O6_REVIEW_20261117.md](O6_REVIEW_20261117.md)；派生数据：[review_20261117.json](../results/20261116-o6-official-adam-cosine-s0/review_20261117.json)。保护O6 250k/320k与O5 Muon32k及既有验收节点，不重启或扩O6预算。

后续[O7计划](O7_OFFICIAL_NOISE_REMOVAL_PLAN.md)、[提示词](O7_CODEX_START_PROMPT.md)和[协议](../configs/o7_official_noise_removal_protocol.json)仅已发布，**尚未部署或启动**。O7将沿用O6配方，只删除官方collection Gaussian；在用户明确调用执行时才按独立身份启动。本次复核发布不启动训练。
