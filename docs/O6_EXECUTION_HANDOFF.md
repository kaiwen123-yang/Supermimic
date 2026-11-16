# O6 执行交接

更新时间：2026-11-17T07:15:05.628564+08:00；实际状态：**evaluating_bones**。

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
保留O1/P6验收及O2/O3/O4/O5历史节点，P12暂停，不开O7。大产物留服务器，不Release/tar/本机归档或阶段清理。
