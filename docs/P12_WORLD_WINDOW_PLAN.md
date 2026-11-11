# P12 执行计划：延长WM拟合窗口，保留原高度残差

状态：**计划已整理发布；实现及服务器训练尚未启动。** 日期2026-11-11（北京时间）。
证据固定提交：`87690ce62dc1a5cf1e8b0fea91f02d9cf30dbae2`。
与 [P11复核](P11_REVIEW_20261111.md)、[机器协议](../configs/next_stage_world_window_protocol.json)、[Codex启动提示词](P12_CODEX_START_PROMPT.md)共同定义下一阶段。本次ChatGPT按用户要求分析并发布计划；用户将启动提示词交给Codex后直接实施和启动，不需要再复述一轮建议。

## 1. 本轮问题与依据

P11高度—速度硬约束正确实施，但候选整体回报低于原残差控制，固定7条同输入WM预测误差也更差。候选完整动作较多，不能简单说所有能力都退化；不过“残差按构造为零”没有成为更好控制的充分条件。P12两路共同回到P11 residual36000父模型，不再沿用速度积分候选作为主线。

这次只研究 **WM拟合窗口k8→k16**。Actor仍H32。当前同输入residual36k在8→16步仍存活区已有误差增长；倒立第16步z低估.100342m时，pre-reward S仍.997672。七窗第8步平均高度误差.012867m，但倒立已错.051820m，所以并非前8步全都准确。到32步时多数窗口模型存活已耗尽，不能拿死后预测爆涨当唯一论据。全部困难clip及有效bin获得曝光也不等于模型已经准确学会关键转换。

假设：在真实连续的16步日志窗口上训练原残差WM，可以改善误差累积，减少不准确的提前跌落，并给策略提供更可靠的预测。是否改善动作优化方向尚待结果，现有轨迹误差没有直接测量Jacobian。是否改善flip/handstand及一般动作/LAFAN保持由正式评分决定。k16不是作者默认，不称已证明根因，也不声称论文的k8必然错误。

## 2. 同父、同配额、唯一配置差异

campaign：`20261111-p12-world-window-s0`。
工作树：`/root/autodl-tmp/robot-repro/supermimic-p12-world-window`。

共同父checkpoint：

`/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency/outputs/runs/20261110-p11-root-height-consistency-s0-full8k_residual_control/checkpoint_0036000.pt`

| 分支 | world_window |
|---|---:|
|full8k_k8_control|8|
|full8k_k16_world|16|

两路完整恢复三网络、三Adam、sampler G/M、已保存Torch/CUDA RNG、全局iteration36000、Actor35995、collected646430720及原全局LR。父已知训练沿革 **431060.78811862133秒** 单列，不称从零。父BONES/LAFAN正式评分和固定7窗WM结果直接复用。

两路均：

- world_root_height_mode=residual；H32、8192真实环境、8192想象batch；
- WM10×4096，Critic5×4和survival_weighted；
- source LAFAN2048/BONES6144；reset LAFAN2048/all BONES5120/hard BONES1024；
- 原hard639仍在all BONES池内，共享恢复G/M，只有两source EMA，重叠hard不重复更新；
- replay每环境1000，collect原2/3交替；共享goal710维，Actor goal encoder追加当前根XYZ误差后713维，另有10×93历史观测；713不是总Actor输入。根反馈尺度.3m、半Actor LR保持；
- aux_bce、analytic_smooth(.05)、gamma=.99、lambda=.95、奖励/PD/噪声/随机化/物理终止及LR日程保持。

唯一研究字段是world_window。不得同时改hard配额、H、终止头、state loss权重、网络容量、动作噪声、Actor/Critic学习率或根高度mode。两路参数形状完全相同，不删head、不迁移网络、不清空Adam。

继续保护P11两路、P10control27000与P9 LAFAN原Critic60000既有锚点，不重评它们；LAFAN已被用户确认复现成功的结论保持。

## 3. 窗口与训练量的准确含义

现有fit_world按world_window自回归，仍从真实s0出发，递归使用自己的状态，动作与context来自同一连续真实日志。k16不逐步注入真实state，也不使用Actor生成新动作替代日志动作。

loss仍是各步原state loss+BCE之和除以k。候选不把loss/学习率机械乘2，仍每联合更新10次WM optimizer step。每轮WM窗口起点仍40960，但预测监督步：

- k8：327680；
- k16：655360。

因此候选的WM计算量和监督预测步翻倍；这不是等算力对照。真实采集、想象batch、Actor/Critic optimizer次数不变；不要为了平衡算力再把候选batch减半或把控制WM次数翻倍。

WM的BCE qpos预取随sample自然扩为[4096,16,36]。**Actor参考窗口仍43帧**，因为H32+goal10没有改变；collect11帧和history10也不改。不得把所有window统一替换为16或扩大完整参考库。

### 连续性与短回合

沿用现有Replay.sample的episode连续性：16步不跨物理终止、自然末尾、训练timeout，终止transition可作为末步。短于16步的实际episode不能提供16步窗口。64步必要fill已足够，不加预训练或恢复演练。

N帧参考的合法16步起点上限是N−17；某些末尾bin可能没有k16起点，但其状态仍可能作为较早起点窗口的后部被训练。k16改变了可用训练起点分布，不把它解释成只增加计算且采样分布完全相同。正常记录实际来源/困难相位曝光，不能为凑样本跨episode、补帧、重采失败状态或自动改curriculum。

## 4. 固定预算与连续执行

每路新增 **9000次联合更新，36001–45000，或累计本新阶段20h，先到停止**。必要64步fill计入阶段；父历史、正式评分、指定证据、Git发布另记。共享资源导致的训练变慢仍计入真实阶段时间。

P11正常k8约5.45秒/更新，其中WM约1.19秒；若候选WM部分近似翻倍，9000轮约需16.6小时。这只是依已有正常运行量的估算，不是新benchmark，也不保证固定墙钟。20h以内结果可以是完整9000轮或真实较早终点，不自动补预算。

若两路各跑满且只有一个新进程：

- 新真实transition各184844288；
- imagined steps各2359296000；
- WM预测步：control2949120000、candidate5898240000；
- 最终Actor44995、collected831275008。

每个真实新进程一次64步fill；此后保持活跃tmux/replay/LR跨窗口连续。实际进程退出恢复才重新作必要fill，并继续累计原P12预算和统计。新阶段统计从零，G/M与全局训练计数继承；不把P11曝光当P12新增量。

单Codex交互窗口≤4h，不因交接停训或重新获得20h。36001起每轮collect→WM→Actor/Critic完整联合更新，不增加WM-only warmup。

## 5. 正式评分与共同节点

完整BONES与LAFAN共同节点为 **39000 /42000 /45000**；时间先到在实际终点两项各做一次，已有同checkpoint评分复用。按iteration−36000排程；父36000已有结果复用。

延续当前实际评分：

- 全130394条BONES，从frame0到原硬终止或自然末尾，分母.1×(N−1)，不套训练500步上限；
- 1024批，按(reference_steps,original_source_clip_id)排序，输出恢复原ID顺序；
- 全BONES、hard639、其余BONES、20类别、四名称技能、既有40h监测、LAFAN分别报告；
- 父成功身份保持/新增/丢失、父+两路共同完整集合质量及奖励分项并列；
- 终点最多8个BONES既定组原id最小两条失败尾窗、LAFAN实际失败短窗，均由同次正式评分取得；
- 全逐clip CSV每1000条，失败保留，不额外物理重放或批量渲染。

主要看flip/handstand是否出现实际能力变化，side_roll/cartwheel是否保持，一般动作与LAFAN是否继续退步；完整数、回报、共同完整质量同时判断。不用训练loss、构造指标或单个短窗判胜负，不挑最佳单点或拼接成功。

终点不同则分别报告，使用已存在的共同正式节点做相同更新比较；不为了凑相同iteration额外训练/物理评分。对“更多WM预测步是否值其计算成本”单列实际时间和工作量。

## 6. 同输入机制证据：只新增两个终点

沿用 `configs/p11_fixed_real_windows.json` 的同一7条P10困难路真实尾窗、同一state/action帧、context33、真实执行动作：
flip180143→175；handstand5→37；reach_jump32→64；flip36055→87；tiger_R00397→129；tiger_R00177→109；side_roll_R00356→88。

共同父residual36000的7×32预测已经发布于：

`results/20261110-p11-root-height-consistency-s0/evidence/full8k_residual_control/`

**直接引用上述父结果，不启动前重复计算。** 两个P12实际终点各在相同输入上预测7×32，共14个rollout、448个新增预测步。无新物理、无Actor新动作、无起点扫描或中间节点重复模型证据。

保留1/4/8/16/32步z/vz/SO3/joint/奖励/终止概率、pre-reward survival以及完整32步小数组。加载器读取实际checkpoint config的root height mode，二路应为residual；k16影响WM训练，不改变此32步共同预测协议。

重点分开：

- 1–8步拟合范围；
- 9–16步，控制超出其k8拟合范围、候选在其k16范围；
- 17–32步，两路都超过拟合窗口；
- 模型仍存活时误差与存活已经耗尽后的误差。

不以死后轨迹极值作为唯一证据，不把7个预选失败窗口当总体随机分布；同输入模型精度改善仍须与真实控制收益对应。

## 7. 正常计算附带的少量统计

继续当前三组LAFAN/hard/其余BONES曝光、height_consistency、per-clip和50帧bin collect/WM/Actor计数、flip/handstand bin物理误差，以及原selected最多4条/千轮。source、bin与实际起点语义不变；k16窗口所有step误差仍归窗口最初frame的bin，并注明这是展开误差。

### 按WM展开步分解已有误差

在fit_world已经算出的squared张量上，按offset j和三组累计：

- z平方误差：70误差坐标2；
- vz物理平方误差：9×坐标37；
- root SO3平方误差：坐标3:6之和；
- 原70坐标平均state error；
- 对应prediction_samples。

control记录1–8，candidate记录1–16。汇总分别给1–8、9–16（candidate）与实际样本数，不直接把16步平均loss与8步平均loss当同长度精度变化。正常replay不同，仍不声称是同输入因果比较。

仅设备端detach累计，按原千轮块/正式节点转紧凑CPU统计；不增加模型前向、backward、随机抽样、梯度扫描或逐步CPU同步。

### 正常窗口接受量

沿现有Replay.sample布尔valid mask顺手累计，记录WM requested/returned窗口数、proposals数、valid_proposals数，按k8/k16分开。接受率是valid_proposals/proposals，不能用returned/proposals，因为现有2倍oversampling会丢弃部分有效超额候选。Actor window1不混进WM分母。

只复用已生成mask，valid.sum留设备，既有节点统一读取；不增.item()同步，不增采样轮数、try上限、CPU日志或重试框架。此统计观察k16的实际选择效应，不触发自动换窗口/配额或补采样。

## 8. 必要代码与配置适配

- 两份实际config：从同父实际配置继承，分别world_window=8/16，world_root_height_mode保持residual；同步新run、campaign、36000起点、45000/20h、发布节点。
- learning.fit_world保持现有按k平均loss与10次optimizer step，只在现有world_error调用补offset索引。网络本体无须改结构。
- HardExposure增加很小的offset×group误差sum/count；保持现有bin坐标、m/s物理单位和新阶段/同run恢复语义。
- Replay接受量仅复用现有mask与draw数量，不更改接受规则。
- 薄P12启动/发布/收尾入口复用现有长度排序、CSV、父保持与共同集合函数；不把P11固定27000/36000常量带进新阶段。
- 收尾按**实际config**计算WM_prediction_steps。旧finish_p11硬编码*8在P11正确，但不能用于k16候选；同样实际记录H32/8192想象量及真实采样量。
- 固定WM证据复用P11 loader及原manifest，父结果直接引用，两端新结果单独保存。
- summary刷新真实latest_training、observed_iteration及训练/评分/发布状态，成本与旧历史分列。

只实施这些任务所需适配，不造通用实验平台、自动搜索或额外验收系统。

## 9. 资源、并行和发布

继续两路8192环境独立tmux并行，GPU训练目标并发2。P11实测每路42544MiB，两路约83.09GiB；其他任务占用按实际共享条件记录。k16只增加候选的WM展开图，持久replay/ActorH32/43帧参考不变。三层2048 MLP多8步的hidden保存张量粗估约1.5GiB，再留其他中间量/allocator余量；不是实测峰值。用真实正式运行的正常节点记录资源，不先做容量benchmark，也不自动增加环境或第三learner。

每训练/评分Torch2线程；已有具体CPU汇总最多12个单线程worker。继续共享原P9同底层只读mmap和manifest，不重筛/重下载/重转/重pack或复制约45.4GiB参考。cgroup120GiB上限与anon/file/inactive_file分清，不拿宿主available决定容器容量；保留当前正常节点资源记录即可。

首路完整恢复、一次fill并进入联合循环后，立即接第二路。正式GPU评分、两端小证据和Git发布共用唯一锁：

`/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`

并发1，训练不占锁；不停止其他项目。训练固定预算不因评分队列延后而自动延长。

P11 control终点发生过实际Git推送失败，最终以**进程级http.postBuffer=67108864**推送既有commit，未重跑训练/评分。P12继承已奏效的现有AutoDL发布路由和该单进程参数；不改全局代理/系统环境，不新建网络监控或自动重试框架。真实错误只针对具体原因修复，不用重评已有分数“恢复”发布。

## 10. 完成交付与禁止事项

按节点推代码、实际config、全逐clip评分、紧凑统计、offset误差/bin曝光、指定448步终点证据与实际失败尾窗、真实结论。完整保留负面结果和技能代价。

原checkpoint每轮保存、最近20轮滚动与里程碑保护照旧。既有工作树、Git/stash、环境、数据、G1资产、用户改动和其他项目保留。大checkpoint、全轨迹、视频、数据和大日志留服务器；不Release、不tar、不推后在用户电脑归档、不自动阶段清理，不把用户自行备份列为研究完成步骤。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量/吞吐benchmark、全盘/无关扫描、额外参数搜索或监控框架。禁止setup、安装升级/重建环境。正常正式训练/评分/规定模型证据按计划直接执行，不把这些必要工作改成另一个测试阶段。

到9000新增联合更新或累计20h停止，完成实际终点评分和轻量推送。若没有改善，解释证据，不自动追加预算、改k/H/配额/损失、加seed/PPO/实机或开启下一阶段。

