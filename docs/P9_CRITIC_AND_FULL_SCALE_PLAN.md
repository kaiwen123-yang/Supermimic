# P9：Critic有效轨迹学习与完整动作库训练

状态：**计划已发布，实施与训练尚未启动**。日期：2026-11-07（北京时间）。依据：[P8深读复核](P8_REVIEW_20261107.md)，固定结果版本`ec870270f56cac91c7bf50b86ced0a8b17cc01ec`。用户本轮已明确要求制定并推送下一阶段计划；P8的“不自动开P9”不阻止本次明确安排。

执行协议：[next_stage_critic_full_scale_protocol.json](../configs/next_stage_critic_full_scale_protocol.json)。启动词：[P9_CODEX_START_PROMPT.md](P9_CODEX_START_PROMPT.md)。

## 1. 研究问题与决策

- 保留H32。P8的H16在九个共同节点全部较差，终点40条R全部低于H32；不继续缩H或加H扫描。
- 修正已证实的终止后Critic目标污染。两路LAFAN从同一H32-51000完整恢复，只改变Critic是否按累计存活权重拟合，正式回答方法收益。
- 同时修正BONES筛选，使用**全部修正后保留动作**，加入固定LAFAN练习份额，启动第三路规模联合训练。无需等LAFAN40/40或稳定性对照结束。
- 第三路使用存活加权Critic候选；它同时改变数据规模、筛选和数据混合，是独立规模研究，不用它给两路Critic消融归因，也不预先宣称该候选已胜出。
- 效率优化仍后置；CPU参考窗口只为让全库训练/评分与另外两路在96GB上并行可运行，不扩成缓存框架或benchmark项目。

保留历史LAFAN指标成功结论。当前H32-51000为R=.8698051557、37/40、C=.9616473230，父37是P9直接基线。B33000和C42000是历史锚点，不沿用父36/37的旧阶段口径。

## 2. 运行位置、共同配置和三路任务

campaign：`20261107-p9-critic-full-scale-s0`。
工作树：`/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale`。
复用主项目现有激活脚本、独立.venv、依赖及G1资产；不setup、安装、升级、重建或清理正常环境，不影响其他项目。

共同源：
`/root/autodl-tmp/robot-repro/supermimic-p8-stability-scale/outputs/runs/20261106-p8-stability-scale-s0-lafan_h32/checkpoint_0051000.pt`。

保留713根XYZ反馈/.3m、公共goal710及未来10帧、history930、k8/H32、aux_bce、analytic_smooth温度.05、Actor LR scale=.5、原奖励/物理终止/PD/噪声/随机化。4096真实环境、4096想象batch、WM10×2048、replay1000、γ=.99、λ=.95、Critic5×4、collect2/3交替、500步训练episode、250000余弦日程不变。每轮真实采集→WM拟合→Actor/Critic完整联合更新。

| job | 初始化 | 研究设置 | 区间/预算 |
|---|---|---|---|
| lafan_h32_control | H32-51000完整resume | 原无权重Critic | 51001–60000，9000联合更新，累计新阶段16h |
| lafan_h32_survival_critic | 同一父完整resume | 只改Critic累计存活加权 | 同左 |
| bones_full_lafan_survival | 同一父三网络weights_transfer | 修正后BONES全库+LAFAN，存活加权Critic | 本数据阶段1–9000，前5次WM-only，累计16h |

两路LAFAN恢复同一三网络、三套Adam、sampler、已保存Torch/CUDA RNG、全局迭代和LR；不重新扩713列，不重置Adam来另造变量。继承了父既有optimizer历史，结论是修正后续训效果，不是从零结果。

第三路仅载三网络权重，新建三Adam、联合数据sampler/replay、seed0 RNG与阶段计数，LR从本阶段起点开始，记录源训练沿革约57.8705h及新阶段成本。源已知训练时间以P8 cost.total_known_training_seconds=208333.7795431018为准；原checkpoint累计时钟字段另保存，不静默修改历史。不同数据不伪装普通resume。

每个新训练进程初始64步replay填充一次。跨Codex窗口的活跃tmux继续使用原进程/replay/LR；实际错误退出后从不含replay的checkpoint恢复，才作一次必要填充并记录成本。16h累计本P9 job实际消耗时间，重启不重置预算，不扣父历史时间，不做恢复演练。数据准备/正式评分成本单列。预算先到发布真实非整千终点，不自动补时或开P10。

## 3. Critic累计存活加权：唯一LAFAN算法变量

令S_0=1，S_t=prod_{j=1..t}(1-d_j)，使用已有想象rollout中**当前reward之前**的累计存活。自然终点沿用 `frame + step + 1 >= lengths[clip] - 1`，以原始clip frame计算；不把collector的500步timeout新增为想象终止条件。几何终止与自然终点仍按原实现进入后续S。

候选目标：
`L = mean(S_t.detach() * (V_t - Rlambda_t)^2) / mean(S_t.detach())`。

实施约定：
1. 两路Actor目标、λ-return递推、H32、BCE和实际终止规则均保持。λtarget仍只生成一次，五轮拟合固定。
2. 首次终止的transition保留此前S_t权重；不能再乘(1-d_{t+1})把这一步奖励/target丢掉。
3. rollout全体B×H的S均值只算一次并detach；每个等长打乱minibatch用自身加权平方误差均值除该**全局固定均值**。不用各minibatch各自sumS归一化。
4. S_0=1保证全局分母为正，不加epsilon、value/target clip、概率硬阈值或新fallback。所有S=1时目标回到现有MSE。
5. 这是针对当前WM失效后缀的方法修正。论文Eq.(3)无此权重，不谎称作者默认或修正抄写错误。
6. 原控制路保持原MSE；正常同一次Critic forward记录raw MSE、上述weighted MSE以及零S后缀平方误差和总平方误差。不新增forward/backward或扫描来计算这些量。
7. 训练日志区分实际优化objective与raw诊断。候选loss较小不作为成果；只按完整动作结果与能力保持作判断。
8. 两路继续保存正常训练样本，每千轮按同一种raw Critic MSE准则选最大更新，再取最多4条最大残差样本。标明旧V/target的参数阶段，保存current S_t、natural_end布尔值与覆盖前的analytic termination probability；真实几何终止记硬计数，想象软概率不新增计数阈值，避免将自然结束都叫跌倒。

ReturnSampler的有限回报/Gmax=10长度偏置另记为已识别机制。本轮两路LAFAN不改Gmax、timeout或采样器算法，第三路组内也保留原算法；记录实际剩余时长分布，避免同时修改多个学习变量后无法判断。

## 4. 修正BONES数据定义，复用已取得的输入

### 4.1 明确修正的两项

**高度语义：** elevated/penetration使用MuJoCo FK后的所有非world机器人body origin的最低z；记录实际body名称。论文未公开其精确body列表，不能将奖励用14个tracked body冒充作者名单。保持>.20m连续.6s、任意<−.12m、超过80%帧<−.08m阈值。浮脚保持两脚碰撞几何到地面>.02m持续.5s及已有明确站立/直立/低速门控；球/胶囊平面对距公式可继续使用，不能把body origin拿来替代foot几何距离。

**名称语义：** 在训练前冻结一份面向外部支撑/地形/对象的清单，来源为论文Appendix E及其引用的SONIC官方处理脚本。至少覆盖论文明示的stair/ladder/box/chair/sit/climb、jump_off_50cm、look_over_fence。采用词边界或完整动作短语，列明实际匹配项；避免box误杀boxing、climb误杀地面mountain_climber等。

可借用的官方支持物项包括bed、bike、chair、sitting/seat/_sit_/sit_、table、ladder、crutch、_ride_、scooter、stair、climb；高度/箱子/边缘短语包括com_up_50cm、step_on、stepdown、box_HSPU、50cm_box_、on_box、fall_from、on_1m、form_box（上游拼写）、off_1m、230m、lift_crate_come_up_、box_jump、box_dips、walking_on_edge、push_obstacle。按“需要当前平地模型没有的实体支撑”解释模糊名称，记录具体选择，不无限扩关键词。

不照搬SONIC的acrobatics_、cartwheel、handstand_ff_、handstand、jump_to_shoulder_roll、kozak_dance、safety_roll排除项；SuperMimic明确以翻转/侧滚作为能力结果。普通腾空、翻转、侧滚、地面起身不能因为难或失败被删。

完整作者关键词与部分浮脚门控未公开，报告本项目具体选择；不以凑129514条或264.56h调参，不按策略评分删动作。

### 4.2 不重下载、不重转所有正确数据

- 复用P8固定revision的原始metadata、已解压G1 CSV和正确NPZ。120→50Hz、cm/deg转换、SLERP和速度定义目前无确定错误，不顺手改。
- 先对metadata作新名称筛选。旧已接受且有NPZ的候选，直接读取qpos做必要FK筛选；保留已有六类参考数组，接受者可通过明确链接/manifest复用。
- 对所有通过新名称规则、但没有现成有效NPZ的候选，从已解压CSV补转换并执行修正后的筛选；包括此前因物理条件或旧名称规则被排除、而新规则允许的动作。必须对全部原始候选应用新规则，不能只从旧133661中继续删，否则无法恢复误排除动作。
- 新数据目录/manifest与P8完全分开，旧40h、旧全库清单、旧评分不覆盖。新完整库为`data/processed/bones_g1_50hz_full_p9`。
- 记录raw/name-pass/physics-pass的逐阶段**唯一条数**、各原因和交集、总小时/帧数、类别及flip/side_roll等名称组的保留数量。排除原因可重叠，不把原因次数之和当排除条数。
- 沿seed0类别轮转原顺序，从新可行全集取完整clip到约40h，冻结一个**监测子集清单**。第三路实际训练仍用全库；全库正式评分后按清单取出40h监测统计，不为该子集另跑物理评分。它不是独立40h训练曲线。
- P8全库原有273.21598h只是历史过滤结果。P9以实际新清单为准，不提前把作者数字写成已处理成绩。

## 5. 完整库与LAFAN共同学习

第三路使用两来源的明确联合数据定义，保留每个clip的source、名称、类别、版本和原长度，避免碰名或隐含拼接。source_id与motion id分开保存，不将LAFAN/BONES同名family混为一种。

固定4096环境：**1024个LAFAN、3072个BONES**。每个环境的来源固定，reset只在相应来源中执行原50% uniform bins +40%当前低回报 +10%记忆分布；每来源内部归一化，不把25%仅写成初始化比例随后被大库bin数吞没。两个来源继续使用同一Actor/WM/Critic并完整联合学习。

replay保持按真实环境记录/采样的现有语义，WM k8有效窗口和Actor起点实际来源比例随正常样本计数报告，不声称严格等于环境份额。25%是针对P8已观测广泛遗忘的本轮固定研究选择，不做比例扫描，也不伪称作者配比。

第三路使用存活加权Critic候选。不要继承P8 BONES9000的退化权重作起点；使用共同源H32-51000的三网络。不同数据的迁移新建sampler/optimizer/计数；同数据resume语义保持。

## 6. 全库参考保留CPU，按训练阶段搬窗口

目前MotionLibrary及evaluate_bones仍会将全参考放CUDA；完整库约45–46GiB，评分进程再复制一份时更不适合三路并行。仅第三路与其全库评估采用CPU连续数组/只读memmap参考存储，GPU保留小型索引元信息及正在使用的窗口；不制作通用cache、自动调参或吞吐测试。

最小调用范围：
- Actor/Critic阶段，一次取frame..frame+H+K，H32、K10，共43帧。六类参考量4096×43×253×4约170MiB。包含末端V需要的未来goal。
- 只预取参考物理数组。每一步goal仍在GPU用当前predicted root quaternion实时变换，不提前固定robot_root特征、不detach方向梯度；当前根XYZ反馈同样保留。
- WM每个k8 batch一次取所需参考qpos；真实next_state已在replay。
- 真实采集每控制步取current/未来10/next参考，reset后的新clip/frame使用新窗口。
- 全库evaluate按现有1024环境批次取参考窗口，不在其独立进程重新全库CUDA；selected rollout导出复用已取数据。
- 分开storage device与learner device，sampler与goal必要张量仍在GPU。两路纯LAFAN保持原驻GPU读取实现，控制路的行为语义不随规模改造变化。

## 7. 正式评估与成本

### LAFAN两路

每1000新增更新完整40动作评估，节点52000..60000，末三58000/59000/60000。复用父H32-51000已发布评分作为起点，不再全量回放父模型。直接父37成功，父3失败为dance1_subject1、fallAndGetUp1_subject1、fallAndGetUp2_subject3。

报告全40R/C/成功身份、父37保持、新增与丢失、起身/跑步、尾三及全节点交集、共同完整集合质量、八项奖励分解。固定终点和共同更新节点为主，不挑最佳单点、不拼接成功并集；旧LAFAN验收不增加门槛。

### 完整库混合路

- 任何更新前保存带联合数据定义的checkpoint_0000000.pt，固定三网络初始化和源成本。
- 在0/3000/6000/9000及真实终点，对**全部新保留BONES动作**正式评分；checkpoint0评分可与训练并行。若实际终点已在规定节点，不重复。
- 在3000/6000/9000及真实终点做LAFAN40保持评分；0点LAFAN复用同权重父评分。第三路BONES与LAFAN评分均通过显式source/评估数据选择入口，分别加载对应子库，记录联合训练定义与实际评估定义。BONES只枚举修正后的BONES clips；不把LAFAN混入其均值，普通训练resume的同数据定义约束保持。
- BONES与LAFAN分开报分，绝不把两个来源合成一个均值来称超过论文。BONES全库、固定40h监测子集、20个metadata类别及flip/side_roll/cartwheel/handstand等固定名称组分别报告R/成功/质量。
- 每clip从第0帧，到真实终止或自然结束；参考N_i帧，分母0.1*(N_i−1)，提前失败不缩短分母。训练500步timeout不用于截断正式评分。
- 本轮计时包括全部训练loop并记录共享GPU；准备/评分/发布单列。第三路含LAFAN经验和源预训练，不能称作者纯BONES从零3h复现。
- 评分串行队列可以落后于训练，结束后发布全部计划节点；训练不等评分锁释放，也不因评分未完成额外延长训练。

## 8. 只补有判别力的证据

### 已有成功—失败轨迹

只从已保存正式评估轨迹导出：
1. H16-50000的dance1_subject1成功轨迹中reference t=104.50..107.14s（frame5225..5357），对照已上传H32-51000同事件失败窗。
2. H32-49000的fallAndGetUp1_subject1成功轨迹中t=6.70..9.34s（frame335..467），对照已上传H32-51000早失败窗。

只新增两个成功小窗及配对说明，保留state/action/reference/实际reward和时间；不重新运行旧checkpoint，不扩大为全动作回放/起点扫描。不把H16成功动作当整体方案更优。

### 正常训练顺带记录

- 既有Eq2、WM分项误差、V/λtarget、阶段耗时继续。
- 从同一正常前向结果记录raw/weighted Critic MSE、S均值、精确零S比例、零S后缀SSE与总SSE；真实几何终止与自然终点分别计数；想象保存natural_end布尔值和覆盖前的analytic termination probability，不为软概率新增阈值。
- 真实reset、实际WM有效窗口、Actor起点按source和参考剩余控制步分组：[1,16]、[17,32]、[33,50]、[51,250]、[251,+∞)。只计已有样本，按千轮汇总，不扫描所有bin、不增加随机采样或推理。
- 每千轮最多4条正常异常rollout，补齐S_t、自然结束标记、source/motion/frame和字段语义。沿用原数量，不存整批B×H。
- LAFAN实际终点失败窗复用评分轨迹。BONES终点评分固定分配最多8个失败尾窗名额：flip2、side_roll2、地面起身/滚动2、其余2；采用冻结manifest顺序，类别无失败则留空。名称组匹配规则在评分前固定，不由最终分数挑选。每个活跃环境用现有有界尾窗缓冲，不保存全库逐帧，不二次回放完整动作。

P8当前大评估JSON在连接器中有读取大小限制；下一轮保留完整逐clip标量，但按固定2000条的紧凑CSV/JSONL分片发布，附字段说明、小型总summary及片段索引。文件是评估数据，不做压缩归档/哈希清单。summary直接给固定共同成功集合、类别质量变化、成功身份差和奖励分解，避免每次只能从巨大文件重新拼结论。

## 9. 并行、交接与发布

- 先实现两路最小Critic开关与正常统计，即启动两个独立训练tmux；同时16个单线程CPU worker修正数据/必要补转换和连续参考存储。第三路材料就绪立即启动，不等两路胜负。
- 目标同一96GB GPU三个训练进程并发，每路Torch2线程。CPU默认16预处理worker，纯数据阶段允许20；总25vCPU下给评分2线程和协调/I/O留空间。已完成的处理不重做以凑核心占用。
- 所有正式评分、规定GPU证据及Git发布共用唯一已有锁：
  `/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`。
  总并发1，正常训练不占锁，不为新工作树另建一把相对路径锁。
- 三路独立run/log/tmux，按实际共享显存接入，不设12GiB限制、不要求独占、不停其他项目。单Codex交互窗口≤4h，后台可持续10h以上，交接不重启正常训练。
- Git先推代码、实际配置、数据定义/过滤统计、全部逐clip评分、紧凑训练统计、指定小数组、结论和服务器位置。计划发布与实际运行状态分别记录。
- 大checkpoint、完整轨迹/视频、原始与处理数据、大日志留服务器；不Release、不为上传打tar、不在用户电脑归档、不自动清理阶段产物。原checkpoint最近20轮滚动保留及里程碑/父/最终保留照旧。
- 禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、无关监控/benchmark。真实运行错误才针对修复；本轮无PPO、多seed、额外H扫描或实机。
- 固定预算后先交付真实结果，不自动续训、改采样算法、扩预算或开P10。

## 10. 预期交付与解释

P9需交付两路可判定的H32 Critic方法对照，以及实际开始/完成的修正全库混合训练与正式评分。若加权路仅loss更小而完整动作更差，结论为未改善；若提高保持同时降低精度，必须同时报告。规模线若只完成数据准备而未启动，不能写成完成规模训练；若成功率高但flip/side_roll和姿态仍差，按真实困难技能报告。

两路方法消融保持单变量。第三路是明确的数据修正、完整库和旧技能练习的联合推进，不把它与P8不同集合/不同来源成本直接当单因素因果对照。
