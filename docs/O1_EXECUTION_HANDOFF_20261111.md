# O1：D57实际准备与接续

**当前状态：O1官方LAFAN40首段训练与正式评分已完成。** 3h节点R=0.8588231143475866、39/40完整，final为R=0.8744398924149845、40/40完整；累计训练11296.659658696502秒，按formal_return_target_reached结束。当前结论见[O1完整复核](O1_REVIEW_20261111.md)、[派生结果](../results/20261111-o1-official-lafan40-s0/review_20261111.json)和[原始汇总](../results/20261111-o1-official-lafan40-s0/summary.json)。作者研究库已取得，旧地址404不再阻塞。下面13:42历史原文完整保留，既不是当前状态，也不构成重启训练、补预算或自动启动BONES/P12的指令。

2026-11-11 13:42（北京时间）。本轮从用户仓库main `db642b3`开始执行O1。官方源码、现有数据索引及执行协议已落地；研究依赖仍不可取得，官方环境未安装，训练与正式评分均未启动。现场记录见[readiness.json](../results/20261111-o1-official-lafan40-s0/readiness.json)。

## 已实际完成

- D57独立工作区：`/root/autodl-tmp/robot-repro/supermimic-official-workspace`。官方源码位于其`supermimic/`，固定`5efbf114e11f725c31d83e217be987c13c0e4ce2`，工作树无修改，保留Apache-2.0许可。上游main本轮未变化。
- 创建`data/`、`outputs/`、`work/`。`data/lafan40_existing50hz`引用`/root/autodl-tmp/robot-repro/supermimic-p4-c0/data/processed/lafan1_g1_50hz`。P6/P7/P9原数据路径也指向这一真实目录。
- [逐动作索引](../results/20261111-o1-official-lafan40-s0/lafan40_index.csv)记录全部40条的原ID、名称、帧数、时长、实际路径和字节数。40个文件均已定位，共414702425字节；既有manifest记录441140帧、50Hz、2.4505555555555567h。没有重新转换或加载动作数组。
- [数据记录](../results/20261111-o1-official-lafan40-s0/data_inventory.json)保留29关节/14身体顺序、原数据revision、插值和速度定义，以及P9的130394条BONES清单和六个现有memmap文件位置。未复制大型缓存。旧主项目的LAFAN目录为空；后续应使用上述实际P4数据位置。
- [O1执行协议](../configs/o1_official_lafan40_protocol.json)固定单卡、seed0、LAFAN40、GenCoord/proprio/history10、12h与3h/6h/12h评分安排，并记录所选上游默认值。该文件是接续协议，尚不是由运行中的官方环境导出的实际config。

本轮只读取旧数据和文件元信息。原`.venv`、Conda base、G1资产、其他源码/工作树与成果未修改；现场已有存储迁移及其他项目任务未停止或改动。

## 当前阻塞与所需材料

本机和D57的已认证`gh api repos/kevinzakka/mjlab_research`均返回HTTP404。[官方Issue #1](https://github.com/HybridRobotics/supermimic/issues/1)仍开放，现有两条回复为其他用户询问，没有作者确认的公开替代版本。404只能证明当前身份无法取得，不能据此断言仓库已删除。

**继续执行必需：作者指定研究库的可访问源码，以及与SuperMimic `5efbf114`匹配的commit。** 官方`uv.lock`仅给出`mjlab`版本1.5.0与`../mjlab_research` editable路径，未记录该研究库Git提交。可以使用作者正式授权的访问来源；不能将普通公开mjlab改名代替。

这个缺口同时包含三类后续必须读取的内容：

| 内容 | 已公开SuperMimic中的实际使用位置 | 尚需确定 |
|---|---|---|
| 多动作MotionLoader | `representations.py`的`motion_ends`和`motion.fk`；`world_model_env.py`的`motion.body_state`；`train.py`传入列表/glob | NPZ实际字段、关节/身体排列、根四元数、速度坐标、fps、clip边界 |
| MotionCommand | runner的`external`模式、`set_sampling_distribution`；viewer的`reset_to_frame` | 精确从clip首帧重置、末帧推进及原硬终止前后顺序 |
| G1真实环境 | `tasks/env_cfgs.py`继承`unitree_g1_flat_tracking_env_cfg` | 机器人资产、物理步长、PD、奖励项和权重、硬失败阈值、DR及seed入口 |

论文历史run config/对应权重、GenCoord或MaxCoord主成绩归属，以及BONES精确成员清单仍未取得。这些影响“论文历史配置复现”的命名与后续BONES对齐；取得研究库后，可按已授权的当前main GenCoord基线推进O1，不需要等待上述历史材料全部齐备。

## 环境与数据接入

新工作区尚无`.venv`和`mjlab_research`；本次非交互PATH未发现Python3.13或uv，`/root/.local/bin/uv`也不存在。没有修改base或安装替代环境。

研究库取得后，将其作为`supermimic`的兄弟目录，记录commit，在本工作区内安装uv/独立Python3.13并按上游`uv.lock`建立`supermimic/.venv`。锁内为Torch2.10.0、MuJoCo3.10.0、mujoco-warp3.10.0.1、Warp1.14.0、rsl-rl-lib5.4.0；这是源码要求，当前尚未安装。

先读实际MotionLoader再做必要字段适配。现有文件的`qpos/qvel/body_pos/body_quat/body_lin_vel/body_ang_vel`等来自独立实现；不能把现有NPZ直接当作者格式。根qpos四元数为wxyz、qvel根角速度为根坐标，具体转换以研究loader为准。保留原40条顺序和原件，输出写入官方工作区的新数据目录。只在确认loader需要后处理数组，不重新下载或retarget。索引中的官方ID和目标路径保持空值，避免预先声称映射完成。

`train.py`支持`--motion-file`的列表/glob输入，并会清空registry引用；完成适配后传完整40条路径。proprio/history10和run名已有公开字段可设置；seed须落实到环境和网络初始化，实际env config在研究库取得后导出。保留官方4096环境、WM10×2048/horizon8、Actor4096/H32、return sampler、normalizer、Muon/Adam等默认机制。

## 最小评测适配设计

这部分目前是按公开源码定位的接入设计，尚未实现或运行官方评分器。

1. 复用`play.py`的`build_world_model`、`build_actor`和权重/normalizer加载路径，改为读取本地固定checkpoint与实际config。使用真实研究环境，Actor设eval；不通过W&B下载模型。
2. 根据研究库明确的API，在每个clip首帧重置。公开viewer已有`MotionCommand.reset_to_frame`调用，但其当前实现随机选帧；正式评分改用确定的clip起点。观测历史沿上游初始帧重复规则构造，随后逐帧滚动。
3. 设置摩擦1、无DR、无观测噪声。`play.py`当前会开启actor corruption，不能直接拿来评分。只取消训练timeout，保持原硬失败与奖励配置；记录首次硬终止transition，不让自动reset后的另一次episode混入累计回报。
4. 每条执行到硬失败或自然末尾。公开WM的最大奖励为`step_dt * sum(正奖励权重)`；正式逐clip分母为这个值乘完整参考转移数。若研究环境确认50Hz、正权重和5，则为旧口径`0.1*(N_i-1)`；未取得环境前不硬编码这个数值。保留完整尾段在分母中，总分为40条逐clip归一化回报的算术平均。
5. 每条输出`clip_id/name/reference_frames/reference_transitions/executed_transitions/reward_sum/max_step_reward/normalization_denominator/normalized_return/hard_failure/termination_reason/completed`及原奖励分项。汇总40条完整/失败数、总体回报和共同完整集合跟踪质量；失败条目全部发布。

研究库的自然末尾与auto-reset时序将决定最后一次transition如何读取，必须先从实际实现落实，不能用公开mjlab推测。`benchmark.py`和交互viewer均不作为正式评分入口。

## 最小保存、计时与发布接入设计

这部分也尚未实施。涉及公开runner的外层运行/产物逻辑，不改变学习目标。

- 在正式进程入口、创建环境/模型之前开始累计训练时钟，使初始化、编译及必要replay填充计入12h。保存collection次数与真实WM/Actor/Critic更新次数，避免把`max_iterations=1000000`当旧实现的联合更新数。
- 在完整collection/learning循环边界记录实际累计耗时，于约3h/6h/12h和实际终点保存不可覆盖的checkpoint目录。达到12h或上游迭代上限后结束本段；若正式评分先达到R>=.82，通知同一训练进程在正常边界保存终点并结束，不自动续加预算。
- 复用`WorldModel.bundle()`、Actor/Critic `state_dict`保存网络与normalizer，同时写本地实际env/runner配置、seed、source commit、计数和耗时。当前官方只存这些网络，`wandb_run_path`仅载WM；不称完整resume。需要退出后续训时再实施必要的优化器/sampler/RNG保存加载，不能把重启当等价恢复。
- 将runner的`_init_wandb`、logger和`log_model_artifact`接到本地日志/保存路径；不调用模型上传或artifact删除分支。不凭`WANDB_MODE=offline`假设`wandb.Api().artifacts`删除路径已禁用。
- 一条tmux `sm-o1-official-lafan40-s0`连续运行，节点评分/发布共用既有`p2-publication.lock`，训练不持锁。评分读取固定节点；训练在另一进程继续时，评价耗时与训练并行时长分别记录，不重复扣减训练时钟。若同步暂停学习评分，则从训练累计时间中扣除该暂停段。
- Git发布代码、实际配置、完整40条评分、紧凑统计和真实状态；模型、数组、日志留`outputs/o1-official-lafan40-s0`。不启动H盘迁移、Release或清理。

## 下一步

取得匹配研究库后，接续上述环境、loader、评测/保存/预算适配，然后直接启动已授权正式run。P12及其他独立实现新实验继续暂缓。当前没有O1 tmux、训练checkpoint或正式分数，12h训练预算尚未消耗；本轮交付为真实源码与数据准备和明确的外部依赖缺口。

