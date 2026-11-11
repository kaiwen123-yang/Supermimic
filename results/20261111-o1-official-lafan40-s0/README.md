# O1 官方LAFAN40：作者研究库已取得

2026-11-11后续检索已取得作者公开的HybridRobotics/mjlab_research@dd51a9f，并采用README更新后的SuperMimic@abc124c。原kevinzakka地址仍404，但源码获取阻塞已经解除。当前正在安装独立环境，40条数据转换及正式运行适配已经完成；这份准备发布不等于训练已启动。

- [作者新地址、固定commit与依赖版本依据](source_resolution.json)
- [官方loader格式与40条逐动作映射](official_data_manifest.json)
- [最新正式接入说明](../../docs/O1_OFFICIAL_RUN_20261111.md)
- [实际解析的环境锁](../../configs/o1_official_resolved.uv.lock)
- [13:42依赖尚未公开时的历史状态](readiness.json)
- [40条实际数据索引](lafan40_index.csv)
- [数据定义、关节/身体顺序及BONES现有引用](data_inventory.json)
- [本轮执行交接与适配设计](../../docs/O1_EXECUTION_HANDOFF_20261111.md)
- [O1执行协议，尚非已解析运行config](../../configs/o1_official_lafan40_protocol.json)

服务器工作区为`/root/autodl-tmp/robot-repro/supermimic-official-workspace`。`data/lafan40_existing50hz`指向现有P4工作数据，40个原NPZ共414702425字节，既有manifest记录441140帧、约2.45056h。初期lafan40_index.csv保留原项目索引；本轮official_data_manifest.json已提供完成转换后的官方ID和目标文件。转换只映射字段/关节顺序及根角速度坐标，没有重新插值或retarget。未执行测试/benchmark。

作者研究源码及commit已取得；论文历史run config和BONES精确清单仍属另一个来源问题。本轮继续当前main GenCoord/proprio/history10首段，无需重新选择路线或批准训练。单卡、seed0、上限12h，约3h/6h/12h和实际终点完整评分，任一正式R>=.82结束本段。训练是否已启动/结束及分数以最新summary.json与D57现场progress.json为准，活跃tmux不重启。

P12继续暂缓；旧成果、环境、数据及现场其他任务均保留。这里没有新的控制效果成绩，不改变既有LAFAN1已达标结论。
