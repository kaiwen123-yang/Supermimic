# O7：在 O6 配方上纳入官方去除采样动作噪声的修正

日期：2026-11-17（北京时间）。状态：**单路从零正式训练运行中**；见[执行交接](O7_EXECUTION_HANDOFF.md)。

协议：`configs/o7_official_noise_removal_protocol.json`；执行提示词：`docs/O7_CODEX_START_PROMPT.md`。本轮依据是 [O6 复核](O6_REVIEW_20261117.md) 和 [原始 O6 结果](../results/20261116-o6-official-adam-cosine-s0/README.md)。

## 1. 只回答一个训练问题

**在已经有效的 O6 fresh Adam＋cosine 配方上，删除真实采样动作的额外 Gaussian 噪声，是否改善 clean 正式评测中的困难技能覆盖和后段保持，同时保住全库精度？**

O6 完整执行到 320000 collection / 127997 joint，最终 R=.9536654882、39 失败、XY=.0517996951m；250k 为 .9532321823、36 失败、XY=.0522944806m。它已避免旧 O4/O5 的全库质量退化。但最后70k collection 修复11条、丢失14条；hard639失败25→28，18条monkey_jump仍只完成1条。≥60秒494条全部完整，尾段平均XY仍从13.87cm增至15.14cm。

[官方提交 7e94b0](https://github.com/HybridRobotics/supermimic/commit/7e94b073940b7a19b9a82ff01e191cfb35c4ba91)报告，Muon/history10、bones_full、300k iterations、2 GPUs在其129514条clean benchmark上，训练有/无collection动作噪声分别2315/1失败；同一段另报告Adam为10/7。作者说明 previous applied action 把采样噪声送回策略历史，Muon后期可能形成依赖。作者iterations与我方collection/joint的精确对应、Adam独立完整配置未公开，不能当作我方单GPU320k的严格同配置对照。

这是作者在论文之后的修正。论文v2 Table A.5本来保留σ=.1，所以O7不称逐项复刻原论文。作者没有公开这组新实验的完整run配置、seed重复、逐clip结果与权重绑定；不得许诺我方39条必降至1。

## 2. 为什么选择这条路线

保留有效的Adam＋cosine，并以已完成O6为参照，能将本轮训练变化集中在官方实际删除的采样噪声上。O6和O7都从零开始，避免把已学到的噪声依赖、旧normalizer和多次权重热启动混进比较。

当前不另开Muon对照：这会相对O6同时改变优化器和噪声，并增加一整条训练预算。O5 Muon32k 的monkey14/18和flip44/44继续作为专项能力参照，不能据此将它与O6逐动作拼成“一个模型”。

O7的收益只解释本seed、本配方、本项目动作库中的这次干预。删除噪声调用会改变之后RNG消耗，seed相同不意味着逐步采样轨迹相同；不据单seed差异作普遍统计显著性结论。

## 3. 固定身份、版本和工作位置

| 项目 | 固定值 |
|---|---|
| campaign | `20261117-o7-official-noise-removal-s0` |
| run | `o7-bones-adam-cosine-noise0-s0` |
| tmux | `sm-o7-adam-noise0-s0` |
| 用户工作树 | `/root/autodl-tmp/robot-repro/supermimic-o7-official-noise-removal` |
| 官方工作区 | `/root/autodl-tmp/robot-repro/supermimic-official-workspace` |
| 隔离官方源码目录 | 工作区下 `supermimic-o7-noise0` |
| 部署适配器 | 工作区下 `work/o7` |
| Python | 工作区下 `supermimic/.venv/bin/python` |
| 官方源码 | `7e94b073940b7a19b9a82ff01e191cfb35c4ba91` |
| 研究库 | `dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd` |
| O6 对照结果 | `8f23f4b26fc84598dc19429963ddb8cd18cd37ee` |
| 配置参照 | `results/20261116-o6-official-adam-cosine-s0/actual_config.json` |

旧abc与新7e历史有分叉，应按快照内容理解变化。精确双树差异是两处采样噪声相关Python删除、CI和uv.lock；不是所有三点compare显示内容都新变了。

**使用O6现有环境，不执行新uv.lock。** O6实际PyTorch为2.14.0+cu130；新lock涉及Torch/MuJoCo/Warp等升级，与本轮问题无关。研究库当前main另有重基，也不一起升级。旧dd51早已用约0.2秒reset bins，新research并没有刚把O6的1秒改成0.2秒。

保留所有旧工作树、未提交改动与历史节点；不动Conda base、MPC-RL、π0、π0.5或其他项目。

## 4. 必要执行适配

从已完成的 `scripts/o6` 复制为独立 `scripts/o7`，将源码部署至 `work/o7`。同步common、driver、launcher、trainer、evaluator、comparison、publisher中的campaign/run/path/protocol/current status，不得只改文档名字后仍调用work/o6。

在7e源码上移植现有O3只读统计patch和O5全Adam WD0分支；O5 patch把已删除的noise字段当作上下文，需针对新源重定位，不能为了patch通过而恢复噪声字段或叠噪语句。保留已经有效的O6 LR原位更新和collection完成判定。

协议已保留O6消费者实际需要的两个顶层对象：`fixed_quality_timeseries.members/timing`（六条完整身份与时序定义）和`completion`。前者是评分器唯一运行配置来源，`passive_diagnostics.quality_series`只是说明性镜像。运行状态以`completion/current_execution`为准，不另留永远为false的重复顶层执行标志。移植时同步common的PROTOCOL_PATH、quality_series读取、publisher的协议目标/文档状态文字及O7 handoff；不让原四条样本标签或O6完成状态混进新阶段。

实际修订的Adam patch保存在`scripts/o7`并随源码发布、记入actual_config；不覆盖旧O5 patch。新增reset组三列放在O7自己的diagnostics扩展/副本，不修改历史scripts/o3/diagnostics.py，包装器必须返回原sampler选中的同一批frames。保留历史评分路径只供只读引用，不再次启动旧read_existing_evidence流程。

关键语义：

- simulator与replay直接接收actor输出。
- **实际删除额外的 `randn_like` 采样表达式；不能设noise=0却仍消耗该次随机数来替代官方行为。**
- 官方load_runner_cfg会忽略旧JSON未知字段；旧参照里的policy.noise不应重新补回。O7有效actual_config明确记录collection noise已移除，不能仍声称活跃σ=.1。
- 传感器噪声、reset扰动、摩擦/COM随机化与原encoder bias行为保持。
- 训练入口不得加载任何历史checkpoint。data_lineage直接读现有manifest，parent=null，wandb_run_path=None，ancestral_joint_updates=0。
- 三网络、normalizer、三套Adam、replay、sampler、RNG均从零。初始化与warm-start不是同一种实验。
- 完成判定沿用O6已修复链路：正常退出且completed collection=320000，训练、评分、发布状态分别记录。旧saved_nodes中的pending是保存时快照，不覆盖完成状态。

只做这次任务所需的源码适配和正常运行观察，不加单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量或吞吐benchmark、通用fallback/监控框架。

## 5. 冻结训练配方和唯一预算

| 配方项 | O7 |
|---|---|
| task / observation | GenCoord / proprio / history10 |
| 数据 | 现有BONES130394，既有packed目录与顺序 |
| 真实环境 | 4096 |
| WM | 每joint 10×2048；horizon8保持官方8状态/7监督转移语义 |
| Actor | 4096 imagined rollouts，H32，gamma=.99，lambda=.95 |
| Critic | 每joint 5轮×4 minibatches |
| optimizer | WM/Actor/Critic全Adam，WD0，eps1e-8，fused/capturable |
| betas | Actor(.9,.95)，WM/Critic(.9,.999) |
| replay | 每环境1000步，replay_ratio16，原Ratio名义.4 joint/collection |
| reset | 原return sampler与约.2s bins，不增加hard配额 |
| 附加采样动作噪声 | 删除；其余训练噪声保留 |
| 完成预算 | 恰好320000 completed collection |

三网使用同一日程，c为**本次从零run已经完成的collection次数**：

```text
lr(c) = 2e-4 × [0.03 + 0.97/2 × (1 + cos(pi × min(c,250000)/250000))]
```

每次self.step完成计数后、当前collection的learner更新前，给所有optimizer group既有设备LR标量做原位fill_；不替换张量、不仅修改cfg、不按WM/critic mini-step另走scheduler。三网设备LR张量在CUDA graph capture之前创建。

| c | 预期joint，仅供解释 | LR |
|---:|---:|---:|
| 80000 | 31997 | 1.54975199e-4 |
| 160000 | 63997 | 6.16994077e-5 |
| 250000 | 99997 | 6e-6 |
| 320000 | 127997 | 6e-6 |

终点预期1,310,720,000 real transitions，WM 1,279,970 / Actor127,997 / Critic2,559,940优化步。以实际计数如实报告，joint预期值不作补步凑数门槛。

没有后台小时截止，没有按回报早停或自动延长。O6实测约11小时只能用于预期成本，不是O7停止时间。单次Codex交互≤4小时，tmux跨窗口连续；交接不重建replay、sampler、normalizer、LR或进程。

若实际训练异常，保存失败状态和真实已有节点。现有checkpoint不含完整optimizer/replay/sampler/RNG，不能从权重恢复后拼称一次连续fresh训练。评分/发布单独失败只继续该阶段，不重训。

## 6. 正式评测与可判读证据

固定正式里程碑为80k、160k、250k、320k与唯一真实终点；initial snapshot及普通rolling20保存沿用O6。训练期间只保存、不评分，训练child退出后只评正式唯一节点。依次加载一次BONES库评全部唯一节点，再加载一次LAFAN40。原已完成O6和O3/O5评分直接复用，不重放旧模型。

BONES4096环境、32个按(reference transitions, source_clip_id)排序的批次，最后3418有效+678 padding；LAFAN40环境。每条从首帧和参考初始状态开始，关闭reset噪声、观测噪声、domain randomization；摩擦1、COM offset0、encoder bias0。保留原hard termination，取消训练time_out时限。

R按每clip `sum(active native rewards)/(0.1*(reference_frames-1))` 后等权平均；包括首次hard failure转移，未执行尾部为0，padding排除。保持原生reward/termination与post-step advanced-reference质量指标的时间语义。

每节点必须报告：

1. 全库R、失败数、完成率和全部逐clip标量。
2. 与O6相同collection节点的修复/新增/持续失败身份。
3. 同一共同完整集合上的R、XY、body orientation和逐动作变化分布。
4. hard639/non-hard、flip44/cartwheel120/handstand160/side_roll22。
5. **monkey_jump18、hook_jump_off_wall12、crutches432**完整组，不能只选最终失败。
6. 全部≥60秒494条长动作；尤其250k→320k。
7. LAFAN40跨库结果；它不重定义O1/P6专门训练LAFAN的既有验收。
8. O7内部250k→320k，以及O6/O7各自固定终点。保护O6两个末节点和O5Muon能力参照，不逐动作拼接最佳checkpoint。

### 同次评分保留六条固定诊断时序

延续O6的16、63672、101155、124371；增加：

| source_clip_id | 名称 | 作用 |
|---:|---|---|
| 1216 | monkey_jump_006__A416 | O6持续失败、O5Muon成功的困难案例 |
| 9457 | monkey_jump_003__A304 | O6后段唯一成功monkey，O5Muon却失败的对照 |

复用现有QualitySeries，stride5+首步+真实最后/失败步；累计奖励保留每个实际物理步。只是保存该次评分已算出的张量，不增加仿真、模型forward、RNG或梯度扫描。新两例的旧O6资料并不齐全：1216有失败短窗，9457主要为标量，不回放补造旧轨迹。

最终失败继续复用现有有界记录器，最多8条×32步。真实机器人与参考的偏差不等于WM预测误差；没有同输入WM预测时不得据此声称世界模型乐观、利用误差或某一高度公式为唯一根因。

### 少量正常训练统计

沿用O6已有日志。只在现有detached reset-membership累积中附加上述三个名称组，使用已选中的frame/clip ID，不新增采样或模型调用。它们是**reset次数/占比**，不是transition份额、WM曝光或成功率。O6没有记录这三个精确组，不能伪造O6对应曝光基线。

## 7. 数据口径：本轮固定，不以失败清洗数据

本次已读全部142220条历史筛选记录：

| 阶段 | 论文v2 | 项目 |
|---|---:|---:|
| 原始 | 142220 | 142220 |
| 名称过滤后 | 129667 | 130655 |
| 可行性过滤后 | 129514 | 130394 |

名称阶段净多988，几何阶段项目剔除261而论文153，最终净多880。未证明两集合是严格包含关系。

项目完整token `crutch` 没匹配复数 `crutches`；当前432条crutches被保留。SONIC源码采用子串过滤，并包含monkey_jump等；现库1167条、O6最终失败24条命中其关键词。**SONIC清单并不等于SuperMimic改编后的清单；不能把39改报15，更不能删880条凑数。**

这些结果已在本次复核中完成，不要求执行端再重复全量过滤/FK/重pack。O7保持130394及全部原评分。作者如果后来公开精确manifest、过滤参数、run config和主结果checkpoint，可以只读记录对应关系；不能改活跃训练数据。严格同作者基准的比较另行明确，不冒充本轮已完成。

## 8. 资源与交付

一路GPU正式训练；需要时用≤12个单线程CPU worker做已有数据连接与汇总。各训练/评分进程Torch2线程。训练不持有发布锁；正式GPU评分和Git发布共用：

`/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`

GPU评分总并发1。复用现有资源，不停止其他任务，不为占满25核/96GB增开无关训练。发生共享资源冲突时等可用资源，不改4096等实验条件做容量试跑。

按实际节点推代码、配置、全部紧凑逐clip评分、已有统计、指定小数组、结论与真实状态。大checkpoint、视频、原始轨迹、大日志留服务器；不Release、不tar、不在用户电脑归档、不自动阶段清理。原rolling20与保护节点规则照旧，用户备份未确认不能标为已备份。

## 9. 完成后的判断

- 如果去噪减少clean失败并保持共同集合R/XY，尤其改善monkey且保住9457，支持该修正在本配方有收益。
- 若失败与精度方向不同，明确报告取舍，不称全面获胜。
- 若大致持平，也符合作者Adam影响较小的观察；不据此自动换Muon、加预算、改H/k、加hard配额或否定作者Muon结果。
- 若monkey等仍集中失败，优先利用本轮保存的真实证据明确下一次要区分的机制，并继续追踪确切作者成员/配置；不直接开启超参网格。
- 每种结果都先交付，不自动开O8。O1/P6验收继续保留，P12继续暂停。

**研究目标是让同一个模型兼顾精度与覆盖，并明确它究竟在哪个基准上达到何种成绩。** 本轮不把达到理论满分1当作论文复现要求，也不将未对齐的0失败或3小时效率标成已复现。

