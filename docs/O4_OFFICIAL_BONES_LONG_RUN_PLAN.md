# O4：官方低学习率方案的较长连续训练

状态：**132000连续联合更新已结束，等待评分**。当前实际状态见 [O4执行交接](O4_EXECUTION_HANDOFF.md) 和 campaign summary；以下保留完整执行方案。

## 1. 本轮决定及依据

从 O3 quarter 的 +32000/final 节点继续使用三网络固定 LR=5e-5，单路连续完成 **132000 次新的联合更新**。保存 +16000、+32000、+64000、+96000、+132000 及实际终点；训练子进程退出后再统一评分。**本段不设后台墙钟截止，按有限更新数结束，不因首次达到某个回报或失败数提前结束。**

O3 在同一父权重、完整 normalizer 和相同配置/seed 下比较2e-4与5e-5；两路都实际完成32000新联合更新。低LR final 的 BONES R=.9443047501120772、130307/130394完整、87失败；control为R=.8920829249218997、395失败。两路共同完整129943条上的R为.9450175952/.8937630374，XY误差为.07176143/.15916211m，优势覆盖跟踪质量和完成数。

但quarter从16k到32k，R .94757578→.94430475，新增69条完整、丢失62条；85665条回报下降。低LR只在已测32k段显示优势，尚未证明更长过程稳定。因此先延长有效方案，不同时改变采样、表示或损失。

### 为什么选132000次，而不只把祖先计数凑到130314

O2 原始连续训练在130314次联合更新时大幅回撤。O3现有checkpoint没有保存optimizer/replay/sampler/RNG，因此O4必须再次权重热启动。父历史31924+32000=63924；若只新增66390或72000，虽然权重沿革总数越过旧130314，**本段新的优化器/replay/sampler仍仅经历6–7万次更新**。

132000让本段自身覆盖旧O2已暴露问题的130314次连续更新范围（多1686次，约1.29%）。它是针对既有风险的一段有限预算，不是盲目按论文表格跑满320000。祖先总计195924只用于溯源。O4与O2初始权重、normalizer历史、LR和数据轨迹不同，不能称严格同初态对照；本段成功也不证明任意更长时间或其他seed永不回撤。

## 2. 身份、父节点和保护

- campaign：`20261113-o4-official-bones-long-s0`。
- run：`o4-bones-low-lr-long-s0`；tmux：`sm-o4-bones-long-s0`。
- D57官方工作区：`/root/autodl-tmp/robot-repro/supermimic-official-workspace`。
- 用户代码的O4工作树：`/root/autodl-tmp/robot-repro/supermimic-o4-official-bones`；保留现有工作树及未提交修改，从最新main准备O4专用适配。
- 父checkpoint：`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o3-bones-lr-quarter-s0/checkpoints/checkpoint_000080006.pt`。
- 父物理节点：quarter/update_32000，final为同一文件别名。父O3新增32000更新、80006 collection、327704576 real transitions；祖先O2 3h另有31924更新、79816 collection、326926336 transitions。
- 保留O3 quarter16k的最高R锚点和quarter32k的较佳覆盖锚点，也保留control全部节点、O2 3h/6h/final、O1/P6验收成果。选择32k为续训父不是删除或否认16k质量优势。
- P12及独立实现新实验继续暂停；本段不自动开启O5。

## 3. 继承官方实际运行配方

复用官方核心 `abc124c1bd5976341034668af3d12c087f2f1f55`、作者研究环境 `dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd`、已有独立Python3.13环境及G1资产。O3诊断源码树为 `supermimic-o3-stability`，原官方源码树不改；可直接复用该已部署、只增加detached统计的树，并记录实际import路径和既有patch。**不要再次对同一树重复apply patch，不重装环境，不切换普通mjlab。**

| 项目 | O4固定设置 |
|---|---|
| 训练数据 | BONES-only，现有130394条packed库 |
| 真实环境 | 4096，seed0 |
| WM | 每次10×2048，horizon配置8；官方实际监督步定义不改 |
| Actor | batch4096，H32，proprio/history10，GenCoord |
| 优化器 | 当前官方Muon/Adam参数分工不变 |
| WM/Actor/Critic LR | 三者固定5e-5，构造learner及CUDA graph之前设置 |
| Replay | 每环境1000，ratio16，对应0.4联合更新/collection |
| 折扣与目标 | gamma=.99、lambda=.95，原Critic clamp和目标定义 |
| 数据、奖励、终止、DR、采样 | 继承O3 quarter实际配置及官方实现 |

不改GenCoord的encoder-bias处理、normalizer算法、根高度积分、k/H、Critic权重、gamma、网络、噪声、PD或成功条件。不加hard/LAFAN配额，不把四分之一固定LR说成论文Adam+cosine的精确重建。

现有数据目录 `data/bones130394_official_packed` 和 `data/lafan40_official_npz` 直接复用；不重下载、retarget、重新pack、恢复全量已清理NPZ或任意删除880条以凑作者129514条。

## 4. 真实恢复语义

`initialization=weights_only_warm_start`，`full_resume=false`。

CPU读取父payload，沿父`runner_cfg`构造新runner；三网络LR先设为5e-5，再创建learner/optimizer及capture。将父WM bundle（含sim-context）、Actor、Critic严格加载到已有对象，保留完整count/mean/var/std归一化缓冲，再做正式collection/update：

```python
runner._wm.load_bundle(payload["world_model"])
runner.policy_learner.actor.load_state_dict(payload["actor"], strict=True)
runner.policy_learner.critic.load_state_dict(payload["critic"], strict=True)
env.reset()
runner._seed_sim_history()
```

optimizer、replay、sampler及随机状态按O3相同规则新建；不假装恢复未保存状态。父normalizer的active count为654630912，正常继续更新，不清零、不冻结。

沿官方冷replay条件`num_transitions >= wm.horizon`和Ratio启动；不加64步/1000步prefill、不加WM-only段、不补恢复演练。初始checkpoint只保存，formal分数直接复用O3父节点。各阶段初始权重一致不等于逐位相同随机样本，报告实际运行条件。

单个Codex交互窗口≤4h，tmux持续运行。交接不得重启活跃训练、replay或LR。若进程真实退出，先记录已完成连续段及原因；不存在full resume时不得自动把重启后的多段拼成一段连续132k，也不得自动重头重跑。按实际有效节点评分、发布明确中断情况，后续决定另行作出。

## 5. 更新预算与必要运行适配

停止条件仅为**本段learning_phases达到132000**、用户明确停止或真实运行错误；`wall_deadline_enabled=false`，`deadline_epoch=null`，`training_wall_seconds_limit=null`。训练实际耗时照实记录，用时不作为后台kill条件，也不把“无墙钟截止”理解为无限更新。

继承`max_iterations=1000000`的collection上界足以容纳本段；按现有Ratio和冷replay起步，预计330006 collection、1351704576新真实transitions，实际计数为准。本段最终active normalizer count预计2006335488；现有int64 count与正常统计公式不改。

O3 driver/trainer含共享deadline及硬编码32000/8000/16000，**必须在独立O4薄适配中改掉实际控制流**，只写文档或把旧budget文件改名不算完成。新适配放`scripts/o4`，部署`work/o4`，复用已有训练、诊断、逐clip评分和轻量发布逻辑；O3历史代码/预算/结果不被重写。明确新的campaign、run、parent、节点列表和输出路径，避免旧O3常量污染结果目录。

两处已有O3硬编码需要一并处理。即时父评分根为`results/20261112-o3-official-bones-lr-s0/milestones/quarter/update_32000/{source}`，历史O2根仍为`results/20261111-o2-official-bones-s0/`；不能把原PARENT_CAMPAIGN一处替换后去O3目录寻找hour_03/hour_06或旧review。比较器改为单路对即时父及相邻实际节点。O4的CODE_ROOT指向新的用户代码工作树；官方源码PYTHONPATH仍指向已有`supermimic-o3-stability/src`，两者用途不同。

复用已部署源码补丁时，首次collection前继续设置`self.o3_diagnostics = CollectionDiagnostics(...)`。共同补丁的step()直接访问该属性；不要仅因阶段改名而换成self.o4_diagnostics。这里保留已有接口，不重复修改补丁。

O3 driver在非零训练退出码时直接抛错、评分门禁要求exit_code==0。O4应在**确认训练子进程已经退出**后，允许仅评分已经实际保存的节点；异常final确已保存才纳入，未保存则不补造。保留训练interrupted/failed及真实更新数，不能因为评分完成便改称132k训练完成，也不自动恢复训练。复用已有异常保存入口，不新增恢复框架。

| 保存标签 | 本段新增联合更新 | 权重沿革总更新，仅溯源 |
|---|---:|---:|
| initial | 0 | 63924 |
| update_16000 | 16000 | 79924 |
| update_32000 | 32000 | 95924 |
| update_64000 | 64000 | 127924 |
| update_96000 | 96000 | 159924 |
| update_132000 / final | 132000 | 195924 |

fixed节点只保存，不在活跃训练期间启动GPU评分。final与132k同文件时只评一次；真实异常终点不伪造132k完成。原普通checkpoint最近20份滚动规则继续，只作用新run普通节点，initial/固定节点/final/被评分引用节点保护。

本段只有一个有价值的训练问题，不为占满GPU额外重复高LR或增开参数扫描。CPU元数据、已有结果分析可并行，最多12个单线程worker；训练/评分各Torch与interop2线程。允许现有GPU共享，记录实际争用，不停止其他项目，不做容量benchmark。

## 6. 正式评分与固定分析集合

训练子进程**实际退出**后，一个BONES worker装库一次，顺序评分五个实际固定节点和唯一异常final；该worker退出后，一个40-env LAFAN worker依次评相同权重。评分及Git发布共用：

`/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`

GPU评分/发布并发1。沿O3已修正的全程inference_mode评分器，BONES按长度排序、4096环境、末批inactive padding。原N帧的归一化分母仍为0.1×(N−1)，完整执行必须覆盖原动作，失败尾部计零，clip等权。禁止用训练episode长度或已存活前缀重新归一化。

所有节点发布全130394逐clip与LAFAN40逐clip，不能只发失败名单或最佳节点。评估不调用WM dynamics/Critic作控制，不增加父checkpoint全量重评。

固定集合见 [O4分析组](../configs/o4_fixed_analysis_groups.json)，仅用于汇总，**不进入训练采样配额**：

- O3 quarter final 的87失败，以及其中父O2 3h原失败残留32和父原成功新失55。
- O2 3h原179失败；O2 3h/6h共同失败57。
- O3 quarter16k→32k丢失62、恢复69、共同失败25。
- 原hard639/non-hard；flip44、side_roll22、cartwheel120、handstand160。
- 新父130307条完整的保留与丢失；各相邻节点共同完整集合的R、XY、根高度/方向、身体姿态及奖励项贡献。
- 参考时长分组与≥60s的494条，防止短动作总数掩盖长动作退化。
- LAFAN仅标“BONES-only训练后的跨库评分”，不称O1遗忘或严格未见泛化。

每节点同时报全部动作与共同完整质量；不能只看完整数。quarter16k与32k两锚点一起呈现，但不按动作选择最佳checkpoint拼接“成功并集”。

## 7. 诊断、失败证据和下一次判读

继续O3已运行的detached统计：collection真实reward/终止及所有done原因episode统计、已有想象dense与bootstrap拆分、raw/clamped value与lambda目标及clip比例、end survival、active normalizer统计和实际reset曝光。保留“collection/reset为窗口总量，loss/imagination为最后一次更新快照”的标签；不得把快照均值称覆盖全部更新的严格均值。

已有sampler在O3 quarter将46.89%的reset分配到hard639；它不是缺乏hard练习的证据。统计reset曝光不等于WM窗口或Actor起点曝光。不增加额外forward、RNG抽样、物理回放、通用监控框架或逐步CPU同步。

实际final从**同一次正式评分**保留≤8条失败尾窗：flip/side_roll/cartwheel/handstand各≤1、other_hard≤2、non-hard≤2，各组原source_clip_id最小者；无失败名额留空。沿O3有界缓冲，每窗≤32条真实transition，k+1状态/k动作，记录原reference frame、context、origin、hard reason和数组语义；不补新rollout或WM预测，不制作视频。

下一次复核主要回答：低LR在本段连续132k中的R、失败数与质量是否保持；剩余87是恢复、迁移成新失败还是恶化；flip/side-roll是否保住，handstand质量与cartwheel覆盖是否恢复。所有五节点和实际final均呈现。R=.90为SONIC回报参照，作者25失败为不同成员集合上的数量参照，不构造新的验收门槛；原LAFAN/O2/O3已取得成果不因后续回撤撤销。

若早期改善而后期回撤，按真实固定节点和诊断定位下一假设，不在本段临时调LR/采样或自动开分支。若最终未到25失败，如实报告，不自动扩预算、删难动作或放宽终止。

## 8. 发布范围与完成状态

先推实际O4适配代码、实际config/来源/计数、五节点全部逐clip、紧凑区间诊断、指定小失败窗、比较结论及现有运行索引。训练前状态只能为planned/implementation_pending，实际运行后再分别填写training_started/training_done/formal_evaluation_done/lightweight_results_published；历史退出快照可保留，但当前状态必须一致。

大checkpoint、完整replay/原始数组/日志/视频/数据缓存留D57；不上传Release、不打tar、不在用户电脑归档、不自动清理旧阶段。沿已有用户管理备份约定，未确认不标记已备份。发布与研究交接不等待用户备份。

将O4启动提示词交给执行端后，执行范围是实现并完成这一个有限更新方案；本次发布计划不代表已在服务器启动。既有O3数据已完整，不重复启动O3；真实错误可针对修复，禁止单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量/吞吐benchmark和无关扫描。完成后交付实际证据和下一步判断，不自动启动新阶段。

