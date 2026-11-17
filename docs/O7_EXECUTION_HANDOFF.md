# O7 执行交接

更新时间：2026-11-17T23:16:04.331295+08:00；实际状态：**evaluating_lafan**。

- collection：320000/320000；实际joint：127997；真实transition：1310720000。
- tmux：`sm-o7-adam-noise0-s0`。已存在budget或活动进程时不重复启动训练。
- 工作区：`/root/autodl-tmp/robot-repro/supermimic-official-workspace`；用户工作树：`/root/autodl-tmp/robot-repro/supermimic-o7-official-noise-removal`。
- 官方隔离源码：`supermimic-o7-noise0`，7e94b073940b7a19b9a82ff01e191cfb35c4ba91；研究库dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。
- 实际统计与Adam补丁均在`scripts/o7`；collection Gaussian表达式已删除，其余噪声保持。
- 实际启动入口：`work/o7/run_d57.sh`；cwd/PYTHONPATH/import均为O7。复用既有Python和资产。
- seed0从零，parent=null，wandb_run_path=None；三网络与normalizer全新，无历史checkpoint加载。
- 全Adam WD0，初始2e-4；每次collection后、learner前对三网全部LR设备张量原位fill_；250k降至6e-6保持到320k。
- 320000 collection是完成条件；127997 joint仅为预期。无后台小时截止、无回报早停。
- 固定80k/160k/250k/320k只保存；训练child退出后依次全BONES和LAFAN评分、逐节点轻量发布。
- 同次正式评分保存协议固定六条时序和final最多8失败尾窗。O6同节点分数复用，不重跑旧模型。
- 训练完成：True；正式评分完成：False；轻量结果发布：False。completion/current_execution是当前状态源。
- driver日志：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261117-o7-official-noise-removal-s0/driver.log`；训练日志：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o7-bones-adam-cosine-noise0-s0/train_official.log`。
- PID/退出：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261117-o7-official-noise-removal-s0/training_child.json`、`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261117-o7-official-noise-removal-s0/training_child_exit.json`。
- 实时训练：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o7-bones-adam-cosine-noise0-s0/progress.json`；节点：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o7-bones-adam-cosine-noise0-s0/nodes.json`。
- 阶段：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/20261117-o7-official-noise-removal-s0/stage.json`；汇总：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/results/20261117-o7-official-noise-removal-s0/summary.json`。

若仅评分失败，在确认没有活动评分后从run_d57.sh --start-at bones或lafan接续；已完成批次自动复用。
若仅发布失败，执行work/o7/publish_results.py --workspace WORKSPACE --label publication-retry；不得重训或重评。
真实训练异常不自动重启；checkpoint未保存完整optimizer/replay/sampler/RNG，不拼接成连续run。
保留O6 250k/320k、O5 Muon32k及全部验收/研究节点，P12暂停，不开O8。大产物留服务器，不Release/tar/本机归档或阶段清理。
