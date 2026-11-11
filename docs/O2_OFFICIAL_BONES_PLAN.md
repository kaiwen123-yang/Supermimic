# O2：官方 SuperMimic 完整 BONES 首段

日期：2026-11-11，北京时间。用户在O1完成复核后确认继续推进。当前来源基点为用户仓库 `95fdcdf0a0d3c594884f3837ad3f8fc0ef953a9c`，官方 SuperMimic `abc124c1bd5976341034668af3d12c087f2f1f55`，作者研究环境 `dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd`。

**本段决定：一条单卡、seed0、从零初始化的官方BONES-only训练，使用现有130394条完整动作，累计训练上限12小时。约3h、6h和实际final保存固定权重；训练进程退出后，先完成各节点的全BONES评分，再完成同节点的LAFAN40跨库评分，发布全部轻量结果。**

本次发布的是已确定的实施方案、机器可读协议和[Codex启动提示词](O2_CODEX_START_PROMPT.md)。新增O2运行适配尚待D57执行端实现，格式转换、训练和评分尚未执行。执行者按本任务完成必要适配后直接进入正式运行，不把O1结束时的“不自动启动下一段”当作阻止本次明确O2任务的条件。

## 1. 从已完成的O1接续

O1从零约3h已达到R=0.85882311、39/40，final为R=0.87443989、40/40，训练约3h8m17s。该项LAFAN1效果复现已经成功，既有P6成功结论也保留。O2不重训或重评O1，也不恢复P12及独立实现的新算法实验。[O1完成复核](O1_REVIEW_20261111.md)

O2要回答的问题是：**已经在LAFAN40跑通的当前官方算法，扩大到项目已有完整BONES库后，能取得什么回报、失败覆盖和困难技能表现？** 本段保持算法、网络、Actor信息、优化器、奖励和采样规则，主要变化为训练动作库。先取得一条含义清楚的官方全库基线。

选择从零的理由是初始化和训练成本可以独立解释。O1权重继续保护，但不载入O2；不另加三网络迁移方案，也不通过 `wandb_run_path` 迁移WM。BONES训练中不混入LAFAN配额或项目旧hard配额。O2的LAFAN结果称“BONES训练后的LAFAN跨库评测”，不称从O1发生遗忘，也不在数据重叠尚未确认时宣称严格未见动作泛化。

## 2. 论文参照与本段目标

论文v2 Figure3(a)明确标出的 **R=0.90是SONIC checkpoint参照**；正文说明SuperMimic超过该回报，没有给出单卡3h主成绩的精确R小数，也没有明确的“R=0.91验收线”。Table A.8公开的失败数为：

| 论文结果 | 数据范围 | 失败数 | 训练资源 |
|---|---:|---:|---|
| SONIC发布checkpoint | 129514条 | 179 | 原论文集群训练 |
| SuperMimic单卡节点 | 129514条 | 25 | 1×H100，3h |
| SuperMimic双卡节点 | 129514条 | 0 | 2×H100，9.8h |

O2报告全库R是否超过0.90，并同时报告失败数、失败率和困难动作；25条失败作为作者单卡结果参照，零失败作为作者双卡结果单列。本地130394条与作者129514条的精确成员不同，不能仅按数目多880条就假设严格包含关系或删880条凑数。达到本地参照指标与严格同成员benchmark分别表述，不因尚缺作者名单而停止当前官方基线。

**本段按固定预算交付，没有R早停条件。** 不使用LAFAN的0.82结束BONES训练，也不把0.90写成作者精确最终成绩。3h、6h、final均保留，避免只给一个最高分。训练完成、评分完成、指标达到哪个参照分别记录；12h是项目首段预算，不是D57必然收敛的预测，也不是论文H100耗时验收线。

依据：[论文v2 §4.1、Table A.5、Appendix E/F](https://arxiv.org/pdf/2610.28480v2)。当前官方main包含Muon/Adam、LayerNorm/GELU等变化，本段仍称当前官方源码基线，不回退优化器去猜测论文历史run配置。

## 3. 固定配置与工作位置

| 项目 | O2配置 |
|---|---|
| campaign | `20261111-o2-official-bones-s0` |
| run / tmux | `o2-official-bones-s0` / `sm-o2-official-bones-s0` |
| 官方工作区 | `/root/autodl-tmp/robot-repro/supermimic-official-workspace` |
| 官方源码 / 环境 | 工作区内 `supermimic/`、相邻 `mjlab_research/`、`supermimic/.venv` |
| O2外层代码 | 用户仓库 `scripts/o2/`，部署至工作区 `work/o2/` |
| 模型与观测 | `SuperMimic-GenCoord-G1`，proprio，history10 |
| 初始化 | fresh seed0；Actor、WM、Critic、optimizer、normalizer、replay、sampler均新建 |
| 真实环境 | 4096，单卡 |
| WM | 每轮10批×2048，horizon配置8，当前实现监督7个后继转移 |
| Actor / Critic | 想象4096、H32；原官方Actor/Critic更新、gamma=.99、lambda=.95 |
| replay / 采样 | 每环境1000步，replay_ratio16，官方return sampler，motion slot1 / velocity0 |
| 学习触发率 | `4096/(10×2048×8)×16 = 0.4` 次联合学习/collection step |
| 训练上限 | 累计43200秒或官方1000000 collection上限，先到停止 |
| 固定节点 | 约10800秒、21600秒与实际final；12h终点不另复制一个同权重节点 |
| 正式评测批量 | BONES固定4096；LAFAN固定40 |

论文Table A.5的SuperMimic单卡就是4096环境。正文8192环境/卡属于PPO-Sim；双卡SuperMimic则是两份4096加跨卡梯度平均，不能等同单卡改8192。当前main单卡将真实env改8192还会改变replay容量和每collection更新触发率，本段保持4096。

Python3.13、Torch2.14、MuJoCo/mujoco-warp3.16、Warp1.18等复用O1已运行环境及实际锁，不重新安装或升级。官方源码不因本段而静默跟随main；旧项目、Conda base、其他项目、Git/stash和用户原件保持。

依据：[O1实际配置](../results/20261111-o1-official-lafan40-s0/actual_config.json)、[官方Runner](https://github.com/HybridRobotics/supermimic/blob/abc124c1bd5976341034668af3d12c087f2f1f55/src/supermimic/runners/supermimic_runner.py)、[官方训练入口](https://github.com/HybridRobotics/supermimic/blob/abc124c1bd5976341034668af3d12c087f2f1f55/src/supermimic/scripts/train.py)。

## 4. 数据：从保留的P9连续数组直接转换

### 4.1 输入与身份

| 用途 | 路径 |
|---|---|
| 原BONES清单 | `/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/data/processed/bones_g1_50hz_full_p9/manifest.json` |
| 共享store | `/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9` |
| 实际只读输入 | 共享store的 `qpos.npy`、`qvel.npy` |
| 新官方packed输出 | 工作区 `data/bones130394_official_packed` |
| LAFAN评测输入 | 现有工作区 `data/lafan40_official_npz/manifest.json` 及对应40个NPZ |

P9联合store先放LAFAN40，再放原BONES清单顺序。BONES清单的 `reference_store.offset=441140`；BONES帧区间为 `[441140,48169048)`。新BONES-only输出从0开始，共47727908帧、130394条；完整参考转移共47597514，在50Hz下约264.430633小时。

执行时从实际manifest读取offset、长度和关节顺序，不靠旧NPZ路径读取数据。`source_clip_id` 是原BONES `clips` 顺序的枚举索引0…130393，原清单并未显式保存同名字段；不能用联合库40+i的ID替代。不重新按名字排序、shuffle、过滤或按策略失败删除动作。

最新清理已经删除历史逐clip NPZ，保留了共享memmap、manifest、P4 LAFAN和O1工作区。因此不再glob旧NPZ，也不需要为了格式转换先恢复H盘归档。[保留记录](../results/storage_export/20261111/npz_cleanup/README.md)

### 4.2 六字段映射

沿用O1已生效的坐标定义，目标关节顺序按固定研究库G1 XML/FK关节名取得：

| 官方文件 | 每帧维数 | 来源 |
|---|---:|---|
| root_pos_w.npy | 3 | qpos[:3] |
| root_quat_w.npy | 4 | qpos[3:7]，wxyz |
| root_lin_vel_w.npy | 3 | qvel[:3]，已经是世界系 |
| root_ang_vel_w.npy | 3 | 用根四元数将qvel[3:6]从局部旋至世界系 |
| joint_pos.npy | 29 | qpos[7:]，按关节名重排 |
| joint_vel.npy | 29 | qvel[6:]，同上 |

root角速度使用O1公式 `omega + 2*cross(v, cross(v, omega) + w*omega)`，其中四元数为 `(w,v)`。世界线速度无需再旋转。不重新求导、插值、retarget、归一化，不平移首帧位置或yaw，也不在转换中添加环境origin。

两个输入以只读mmap打开；输出六数组以float32 NPY分块写入，建议每块131072帧、单进程顺序读写。这是一次必要格式转换，主要工作是连续I/O，不需要多开13万小文件或读入四个旧body大数组。官方在访问参考帧时计算身体FK。

额外输出：

- `motion_ends.npy`：int64的 `cumsum(frames)`，exclusive边界，不带前导0、不减1、不保留旧441140偏移，末值47727908。
- `joint_names.json`、`motion_names.json`：官方关节名顺序和原BONES动作名。
- 完整clip索引：official_clip_id、source_clip_id、name/category/package、frames、reference_transitions、源store起止、新packed起止；原source_path仅用于溯源，不重新打开。
- 小型来源与完成记录：实际输入、repo/revision、50Hz、单位/坐标、转换时间、总数与输出目录。完整索引进Git可按2000条分片，六大数组留服务器。

训练把 `cfg.commands['motion'].motion_file` 直接设成**该单一packed目录字符串**，不把目录拆成字符列表、不展开成六NPY，也不与LAFAN的NPZ混成list。官方loader已支持该入口，不改写loader。

依据：[O1转换代码](../scripts/o1/convert_lafan.py)、[P9数据构建](../scripts/prepare_bones_p9.py)、[官方MotionLoader](https://github.com/HybridRobotics/mjlab_research/blob/dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd/src/mjlab/tasks/tracking/mdp/commands.py)。

### 4.3 资源含义

六字段共71个float32/帧，BONES静态参考约12.624GiB。官方packed loader普通 `np.load` 后把整套六数组搬到device，不是CPU memmap按需GPU窗口。当前4096×1000 replay字段静态约3.929GiB，另有仿真、模型、优化器、想象激活、CUDA图与sampler，不能将13GiB当总训练显存。

记录正常启动/节点的实际显存、训练耗时及cgroup内存即可，不进行容量或吞吐benchmark，不凭容量增加第二条learner。D57已有硬件记录是RTX PRO6000 Blackwell Server Edition 96GB、25vCPU、120GiB容器RAM；其他任务按原安排继续。

## 5. 训练与评分顺序

一条tmux负责整个正式段，外层驱动依次执行：

1. 完成必要薄适配和packed转换；发布实际数据来源、代码和配置。
2. 启动唯一正式训练子进程；保持官方学习闭环，正常节点保存3h/6h/final权重和实际计数。
3. 等待训练子进程真正退出，释放训练replay、图、模型及全库引用。
4. 启动一个BONES评分进程，加载全库一次，依次加载3h/6h/final权重，各自完整评分全部130394条；每完成一个节点发布其轻量成绩。
5. BONES评分进程退出后，新建40-env LAFAN评分进程，依次评同三个O2节点；不同时驻留两份库，不重评O1权重。
6. 写完整总结和真实状态，发布所有已算结果，结束本段。

训练时钟从正式进程导入重依赖前开始，包含全库载入、环境/网络初始化、编译和必要replay积累。数据转换、评分、发布分别计时。训练中的共享硬件争用仍属于真实训练墙钟，不人为扣掉。训练期可在节点先推轻量配置/计数和“评分待执行”状态；正式全库结果在训练结束后才产生。

O1的 `save(label)` 会立即启动异步评分，连final也在清理前启动；O2必须将所有节点改成只保存和登记待评分路径。不能只调用 `env.close()` 就假设所有显存已释放，由外层等待训练子进程退出最直接。O1的 `.82` stop文件写入和读取逻辑全部不进入O2。

单Codex交互仍≤4h，tmux训练与后续评分可跨窗口连续。交接读取现有状态，不重启活跃进程、不重建replay、不重置LR或重新获得12h。若发生真实错误，针对该错误处理并记录已耗时间和实际恢复方式；网络权重恢复不称full resume。无需为预防假想故障新增恢复框架或演练。

## 6. 全库正式评分的必要适配

### 6.1 批次与模型

复用O1评测的 `build_world_model`、`build_actor` 与同checkpoint normalizer加载；不实例化完整训练Runner。BONES建立一个固定4096-env、一个MotionLoader，三个节点在相同对象上换权重并重新reset；模型置eval，统计冻结。LAFAN另建40-env，同样加载O2各节点权重和统计。

只对**评测任务ID**按 `(frames−1, source_clip_id)` 稳定排序，邻近长度分批；不重排packed数据本身。130394条共32批，末批3418条真实动作和678个inactive填充槽。全部批次复用同一环境，padding不进评分、计数或输出。

### 6.2 不同clip起点的批量reset

作者 `MotionCommand.reset_to_frame(env_ids, frame)` 的frame是单个int；不能直接传4096个不同起点tensor。外层用薄helper复用该方法内部已有操作，不修改官方源码：

```python
base.reset()  # 正常清除action、计数及manual-reset状态
ids = torch.arange(batch_size, device=device)
frames = batch_start_frames  # int64，各自clip的起点；填充槽也使用合法帧
motion.set_time_steps(ids, frames)
motion._write_reference_state_to_sim(
    ids,
    motion.motion.root_pos_w[frames] + base.scene.env_origins[ids],
    motion.motion.root_quat_w[frames],
    motion.motion.root_lin_vel_w[frames],
    motion.motion.root_ang_vel_w[frames],
    motion.motion.joint_pos[frames],
    motion.motion.joint_vel[frames],
)
base.scene.write_data_to_sim()
base.sim.forward()
motion.update_relative_body_poses()
base.sim.sense()
obs = base.observation_manager.compute(update_history=True)
base.obs_buf = obs
history = obs['actor'].unsqueeze(1).repeat(1, 10, 1)
```

官方state写入保留原soft joint limits、速度和robot reset。相对参考、传感器与历史必须在写入后刷新；不循环13万次单环境reset，也不以只写qpos代替完整reset。

### 6.3 固定评价口径

保持O1已经核对的原生reward/hard条件：摩擦1、COM与encoder偏移0、确定性Actor、无观测噪声或起点扰动；取消训练time_out，auto_reset=false。

每条完整转移数为 `N_i−1`。用进入该步前的active累计真实奖励、质量和步数，先保留hard标志，再关闭失败/完成行。若还要继续全批step，显式reset**所有**terminated或truncated行，包括已inactive及padding行，满足原生manual-reset义务；active只控制计分。下一批正常reset后重新铺10帧历史。

逐条 `R_i = reward_sum / [0.1×(N_i−1)]`，失败尾段保留在分母。全库为130394条的算术平均，**不直接平均32个batch均值**；末批有效数不同。完成比例也按clip等权，总执行步/总参考步另列。40条LAFAN独立汇总，不和BONES合成一个总分。

完整表示完成N−1转移且无hard failure，不把 `natural_end` 文本当作底层motion_end一定触发。reward/termination沿用上游内部时序；quality采用O1的返回后刷新状态和推进后的参考，明确记录，不能由质量均值直接反算reward。

## 7. 报告与必要证据

每个正式节点保存全部逐clip行，包含原ID/名称、参考帧/转移数、执行数、reward sum、归一化分母、R、完成比例、hard reason、各奖励项及O1已有几何质量均值。分片按实际行数累计并建立小索引，BONES按2000条分片；LAFAN用40行CSV。评分未覆盖全库时明确标为进行中，不能把局部平均写成全库成绩。

同一批次只做一次真实评分。既有已完成分片保留；实际评分中断后从未完成批接续，不因发布失败重训或重评。按长度执行后输出可还原原ID顺序；各节点以同一原ID作共同完整集合比较。

汇总至少包含：

- 全库R、完整/失败数、失败率、等权完成比例、总执行/参考转移数、奖励贡献及XY/姿态质量。
- 原category分组，以及冻结hard639与其补集；flip、side_roll、cartwheel、handstand等用原元数据定义。hard仅用于分析，训练不加配额，不按本轮失败更新名单。
- 3h→6h→final的新增完成、丢失完成、共同完整集合质量；不得拼逐clip最佳节点。
- LAFAN40跨库成绩、6条起身和4条跑步等原分组；与O1作为不同训练数据/初始化的参照，不称同父能力保持。
- collection、真实transitions、联合学习、WM batch、Actor及Critic更新数，实际训练与评分耗时；未发生的节点不补成零值或伪造计划时间。

最终节点同次BONES评分可保留**最多8条、每条最多32个真实转移的小证据窗**：flip、side_roll、cartwheel、handstand各最低source ID失败1条，再取其他hard2条、非hard2条；类别互斥、去重，数量不足不补重放。窗口截止并包含首次硬失败转移，实际长度 `k=min(32, 该clip本次已执行转移数)`；保存 `k+1` 个状态帧、`k` 个动作/奖励、参考状态与帧ID、context、首次失败原因及 `valid_length=k`。只从同次执行的有界缓冲提取，不足32步保留实际长度，不padding、不补造历史、不跨clip或reset取帧、不因轨迹短更换已选候选。小证据进Git，完整轨迹/视频不在本段生成，不追加同动作重放、WM预测或其他模拟。

评分与Git发布共用现有 `p2-publication.lock`，总并发1；训练不持锁。纯CPU元数据分组/汇总可以并行，最多12个单线程worker；Torch训练和评分各2线程。数据转换用大块顺序I/O；不为占满设备而另开未定义训练对照。

## 8. 执行端应实现的最小文件

下列为**待实施入口**，当前计划提交不声称这些脚本已存在或已经运行：

| 用户仓库入口 | 必要职责 |
|---|---|
| scripts/o2/pack_existing_bones.py | 两份只读mmap到官方packed，输出完整身份索引和真实转换记录 |
| scripts/o2/train_official.py | 复用O1外壳，改单目录、fresh初始化、节点只保存、固定预算；学习调用保持官方 |
| scripts/o2/evaluate_library.py | 固定批量、批量起点、同库多节点、逐clip分片、同次有界终点证据 |
| scripts/o2/publish_results.py | 复用现有轻量发布，改O2/双数据源/完整数；仅提交新分片与变更汇总，避免重复上传全历史 |
| scripts/o2/run_d57.sh及必要小helper | 复用O1独立环境，串行驱动转换→训练进程退出→BONES评分→LAFAN评分→收尾 |

无需改官方学习器、MotionLoader、sampler、reward、终止阈值或网络。只读分组逻辑可复用旧p10_metrics，但不得导入旧独立仿真器/Actor/训练算法替代官方。实现完成后推实际代码及config，再直接进入已定义正式段；不增加单元/mock/冒烟/导入/形状/哈希测试、恢复演练、benchmark或参数搜索。

## 9. 保存、发布与交付

服务器run目录为工作区 `outputs/o2-official-bones-s0`；结果目录为 `results/20261111-o2-official-bones-s0`。checkpoint包含官方三网络、normalizer、runner实际配置、数据来源、计数和实际时间。当前方案不提供完整optimizer/replay/sampler/RNG恢复，明确 `full_resume=false`。

复用用户允许的普通checkpoint最近20份滚动保留，保护初始、3h、6h、final及被正式评分引用的权重；仅作用于新O2 run的普通滚动文件。O1与历史保护节点、输入数组、环境和源码不清理。大权重、全日志、packed数组继续留服务器，不Release、不tar、不自动归档到电脑、不进行阶段批量删除。

Git发布实际代码、协议与实际配置、数据索引、各节点全部逐clip分片、紧凑训练/评分统计、指定小证据、结论和当前状态。更新README、AGENTS、results/index与campaign summary，区分planned、training、training_completed_evaluation_pending、evaluating和completed。完成是所有实际固定节点的两种评分与轻量发布均结束，不被旧训练退出快照误导。

到本段预算如实交付，后续按真实结果决定研究方向。本段不自动增加seed、训练变体或O3，不重跑P12；LAFAN既有验收成果保持。
