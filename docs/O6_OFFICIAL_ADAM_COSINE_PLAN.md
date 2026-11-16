# O6：从零完成官方 Adam＋cosine 训练路径

日期：2026-11-16（北京时间）。状态：**正在LAFAN跨库评分**；见[执行交接](O6_EXECUTION_HANDOFF.md)。 本轮依据已完成 O5 的 [复核](O5_REVIEW_20261116.md) 与 [原始结果审阅](../results/20261115-o5-official-optimizer-s0/review_20261116.json) 制定；O5 不重启、不扩预算。执行入口：[Codex 启动提示词](O6_CODEX_START_PROMPT.md)；机器协议：[o6_official_adam_cosine_protocol.json](../configs/o6_official_adam_cosine_protocol.json)。

## 1. 本轮回答的问题

O3 降低固定 LR 的短段收益成立，O4 已表明固定 5e-5 无法保持长段质量。O5 的 Muon WD0 终点为 R=.91915658、50 失败；Adam WD0 为 R=.92838634、90 失败，两者均低于共同父的 .94430475，Adam 的 16k→32k 仍有质量回撤。去掉衰减或改成固定低 LR 的 Adam，没有单独解决精度保持。

本轮从零执行一次完整的**官方代码＋论文 Adam/cosine 日程**。从零初始化消除 O2→O3→O5 继承权重、normalizer 历史和多次优化器重建的混合影响；全程按明确日程走到低 LR 保持段。若改善，结论是这条完整配方在本 seed、本库和有限预算下有效，不能只归功于 cosine。

O1/P6 已达到的 LAFAN 指标继续保留。P12 暂停。BONES 项目库的 .90 参照已经达到；本轮重点同时考察整体回报、完整数及共同完整动作的跟踪质量，尤其 250k→320k 的保持情况。

## 2. 配方和公开材料的边界

固定官方 `HybridRobotics/supermimic@abc124c1bd5976341034668af3d12c087f2f1f55`、作者研究库 `HybridRobotics/mjlab_research@dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd`，复用现有 Python、依赖、G1 资产和动作数据。

| 项目 | O6 设置 |
|---|---|
| 初始化 | seed0；WM/Actor/Critic、normalizer、optimizer/replay/sampler/RNG 全新；parent=null |
| 数据 | BONES-only 130394；LAFAN40 只作跨库评分 |
| 表示与输入 | GenCoord、proprio、history10 |
| 真实采集 | 4096 环境；原 return sampler、奖励、终止和随机化 |
| WM | 每 joint 10×2048；官方 horizon8，实际为8个存储状态、7个受监督转移 |
| Actor / Critic | Actor4096、H32；Critic5 epochs×4 minibatches |
| 优化器 | 三网所有参数均 Adam、WD0；Actor β=(.9,.95)，WM/Critic β=(.9,.999) |
| 学习率 | 初始2e-4；250k collection 余弦降至6e-6，保持到320k |
| 其余 | gamma=.99、lambda=.95、replay_ratio16、joint/collection=.4；沿用 O5 实际非优化器配置 |

[论文 v2 Table A.5](https://arxiv.org/pdf/2610.28480v2) 给出 Adam、cosine 到 .03 倍/250000 iterations、总320000 iterations。当前及 Muon 前公开 runner 的 max_iterations 均计外层 collection。O6 明确采用该公开代码口径；**这不是已经取得作者原始 scheduler/run 配置的证明。** 主成绩的 GenCoord/MaxCoord 归属、129514与130394的成员关系，以及当前源码后续变更与论文配置的精确对应仍未解决。

当前官方 horizon8 的实际转移数、GenCoord 实/想象 encoder-bias 语义差异继续记录。本轮不顺手修改它们，不冻结 normalizer，不加 hard/LAFAN 配额，不换网络、奖励或表示。WD0 是本轮显式选择及公开 Adam 默认，不称论文表格另列了 WD0。

## 3. 时钟、LR 与正常完成

`c` 是本次已完成的 `self.step()` 次数，初始为0。每次采集完成后 c加1，在任何 learner update 之前更新实际 LR：

```text
lr(c) = 2e-4 * (0.03 + 0.97/2 * (1 + cos(pi * min(c,250000)/250000)))
```

三个 Adam 的 device LR tensor 在 CUDA graph capture 前构造。之后遍历 `world_model_learner.optimizers`、`policy_learner.actor_optimizers`、`policy_learner.critic_optimizers` 的所有 param_group，对原 LR 对象原位 `fill_`；不替换 tensor、不只改 cfg、不按各 optimizer.step 单独推进 scheduler。初始 cfg LR 与实时 group LR 分列记录，不新增验证更新或 probe。

| 完成 collection c | 预计实际 joint | LR |
|---:|---:|---:|
| 80000 | 31997 | 1.5497519911e-4 |
| 160000 | 63997 | 6.1699408718e-5 |
| 250000 | 99997 | 6e-6 |
| 320000 | 127997 | 6e-6 |

保留原 Ratio(.4) 和 replay fill：step0/3/5 学习机会因不足8状态跳过，首实际 joint 在 step8/c9。预期终点为127997 joint、1310720000真实 transition；它们是静态推导，以实际计数为准，不补跑凑数。

**正常终止条件是完成320000 collection。** 显式设 max_iterations=320000，移除 O5 的32k joint截止和所有旧小时deadline。trainer、common.training_state、publisher、summary/index/handoff 必须一起按 collection 判断完成：原 O5 会把 `collection_iteration_limit` 标为 interrupted，不能沿用该分支；O6 正常达到c320000应标训练完成，缺点评分另记。不能将预计127997 joint设为新的完成硬门槛。

正式节点 collection80k/160k/250k/320k只保存，训练实际退出后评分，final同一物理checkpoint去重。不按回报早停、不自动延长。单个Codex交互窗口≤4h，后台tmux跨窗口连续；已有活动O6只观察接续，不重建replay、重置LR或重复启动。

当前保存不含 optimizer/replay/sampler/RNG完整恢复状态。真实进程异常时保留failed/interrupted与已有节点，不以weights-only重启拼接成同一个连续run；评分或发布失败只接续对应阶段。

## 4. 必要适配和工作位置

- campaign=`20261116-o6-official-adam-cosine-s0`；run=`o6-bones-adam-cosine-s0`；tmux=`sm-o6-adam-cosine-s0`。
- 用户工作树：`/root/autodl-tmp/robot-repro/supermimic-o6-official-adam-cosine`；仓库适配器放 `scripts/o6`。
- 官方工作区：`/root/autodl-tmp/robot-repro/supermimic-official-workspace`；**部署目录统一为该工作区的 `work/o6`**。新隔离源码树为 `supermimic-o6-adam-cosine`，Python复用 `supermimic/.venv/bin/python`。
- launcher的实际命令、cwd、PYTHONPATH、driver与import来源全部改到O6；不能继续执行 `work/o5/driver.py`。在新干净官方树各应用一次O3统计补丁和O5优化器补丁，保留 `self.o3_diagnostics`；原O3/O4/O5树不改。
- 从O5 actual config复用非优化器字段，但显式 `wandb_run_path=None`；移除parent加载和initial父评分依赖。data_lineage直接取已有packed manifest，祖先更新数为0，不再读取 `parent['data_lineage']` 或 `protocol['parent']['lineage_joint_updates']`。
- driver/common/comparison/publisher清除两臂、8/16/32k joint节点、历史大checkpoint范数读取、旧父保持率和版本字段；元数据写fresh/parent=null及实际O6 source/import/patch。

不安装、升级或重建环境，不改Conda base及其他项目。等待实际可用资源时不缩batch、不停止他人任务、不做容量/吞吐benchmark。

## 5. 有价值的并行任务

GPU只执行这一条完整fresh配方；训练/评分各Torch与interop2线程。CPU只读工作最多12个单线程worker，可与训练并行：

1. 核对公开作者run配置、精确动作清单和筛选规则与本项目的对应。仅使用可取得原件；不能将演示checkpoint当论文主结果checkpoint，不能删880条凑129514，也不能根据策略失败过滤数据。缺原件如实记缺口，不阻断已明确的O6运行。
2. 阅读已保存原始结果中“完整执行但位置/姿态质量回撤”的动作，整理下节固定四条的既有证据。若服务器没有历史原始轨迹，记录缺失，不重新跑旧checkpoint或新增网络前向。

不为占满显存新添固定Adam、多seed、MaxCoord或其它训练对照。若O6改善，不把历史O2/O5当严格等条件的cosine消融对照。

## 6. 正式评分与紧凑时序证据

训练child真实退出后，一个4096-env BONES worker装库一次，按长度排序32批依次评所有实际正式节点；最后3418有效、678 padding inactive，整批inference_mode。随后一个40-env worker评LAFAN。GPU评分/发布共用既有 `supermimic-p6-position-feedback/work/p2-publication.lock`，并发1，训练不持锁。

评分沿用每clip `sum(native reward)/[.1*(N-1)]`、失败尾段零、clip宏平均和原生失败条件。发布全逐clip、hard/non-hard、flip/side-roll/cartwheel/handstand、时长分组、相邻及固定多节点共同完整集的R/XY/body orientation。历史O3 quarter16k/32k与O5 Muon32k、Adam16k/32k成绩直接复用；O6跨历史成功交集不能叫父保持或O1遗忘。

既有失败尾窗只描述真正触发失败的少数动作，不能解释主要的完整动作精度回撤。本轮增加**四条预先冻结动作的紧凑位置/姿态时序**，成员、来源和分组写入协议，包含已知回撤动作source_clip_id63672；分为一条性能分化动作、一条稳定对照、两条≥60秒位置回撤动作。名单由O5已发布逐clip结果冻结，不按O6结果更换；不是代表性随机样本，也不加入训练配额。

| source_clip_id | 动作 | 固定原因 |
|---:|---|---|
| 63672 | jog_ff_loop_270_002__A181 | 父/Muon/Adam均完整，R=.772073/.850559/.344369，观察改善与回撤分化 |
| 16 | body_stretch_V001_003__A272_M | 三者均完整且R>.985，稳定对照 |
| 101155 | Idle_Left_001__A017 | 76.52秒均完整，父/Muon/Adam XY=.123532/4.308207/.217730m |
| 124371 | Idle_Left_001__A019 | 76.52秒均完整，父/Muon/Adam XY=.065463/.154850/1.187028m |

只在O6各节点的同次既定正式评分中，顺手保存这四条已有张量的时间序列：参考帧/时间、活跃与终止标志、机器人/参考anchor XYZ及其delta、根XY/Z/方向误差、相对body位置/方向误差、原生reward/奖励项及其已有累计量。每5个正式评分步记录一次，另含第一个计分转移及末步/失败步；设备端缓存少量选定张量，批次结束再搬CPU。正式R仍由每个物理步完整累计，不能用抽样时序近似替代。

按实际执行前缀保存、不padding，不加网络前向、RNG抽样、物理重放或批量渲染。若某条在O6失败照实保留原名单与终止，不替换为新“成功”动作。数组以小NPZ保存并附字段、计时/参考推进口径、env_origin和source ID，允许进入轻量Git发布。

final仍可保留最多8条真实失败各32步尾窗，来自同次评分；两种证据用途分开。anchor_pos是z-only，anchor_ori是投影重力z分量差；原生终止时点与post-step/已推进参考的质量时点不同，不拿最后一帧机械重判终止。

沿用正常采集窗口总量与最后joint的loss/value/gradient快照、raw/clamped value/GAE、normalizer、实际参数范数和优化器元数据；区间总量与快照分开解释。动态LR、collection/joint/transition计数同记，不新增测试或诊断前向。

## 7. 判断、交付和保护

主要比较250k→320k低LR保持段的全库R、覆盖及共同完整质量，再结合80k/160k判断学习路径。较少失败不能掩盖精度下降，也不能将不同checkpoint逐动作最好结果拼成一个策略。若改善，只确认本次完整配方；若仍回撤，交付现有证据，不自动扩时、加seed或开O7。

轻量推送实际代码/patch/配置、全部逐clip、紧凑日志与时序、真实结论，并同步AGENTS/README/index/handoff。保护O3/O4/O5全部既定节点及O2/O1/P6历史成果；O6固定、final和被评分节点保留，普通最近20个checkpoint滚动规则不变。

大checkpoint、完整日志/视频/轨迹留D57；不Release、不tar、不用户电脑归档、不自动阶段清理。不新增单元/mock/冒烟/导入/形状/哈希测试、恢复演练、benchmark、全盘扫描或通用防御框架。**当前部署、训练、评分状态见执行交接与campaign summary。**
