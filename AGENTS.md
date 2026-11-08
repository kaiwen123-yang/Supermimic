# SuperMimic 执行约定

本仓库是用户的独立论文复现项目，远端为 https://github.com/kaiwen123-yang/Supermimic 。

## 复现验收标准（用户最新确认）

用户确认验收标准（2026-11-05）：**达到作者对应实验的指标，就算该项复现成功。当前LAFAN1全40正式评估回报目标0.82，P6 B33000为0.86624655，因此已认定LAFAN1指标复现成功。** P7属于达标后的巩固与研究，不是复现成功的前置条件；不追加40/40、从零重训、更多seed、H100同等耗时、BONES或实机等验收要求。已保存B33000的达标结论不因后续研究节点回撤而撤销。

## 当前任务与证据

- 当前P10计划已发布，尚未实施/启动：docs/P10_8K_HARD_PRACTICE_PLAN.md、configs/next_stage_8k_hard_practice_protocol.json、docs/P10_CODEX_START_PROMPT.md。本次用户明确要求推送下一步并扩大环境，旧P9“不自动开P10”不覆盖新的授权。按启动提示词实施时接续P9 full9000，不重新跑P9。
- P9三路训练、全部正式评分与轻量发布均已完成。LAFAN原Critic60000为0.89043870/38完整，加权为0.84312458/36；全库9000为0.84379710、129220/130394，264.430633h，LAFAN保持29/40且起身0/6。复核见docs/P9_REVIEW_20261108.md及results/20261107-p9-critic-full-scale-s0/review_20261108.json，实际完成状态见该campaign的summary.json。
- P8已经全部完成：results/20261106-p8-stability-scale-s0/summary.json、conclusion.md。H32/H16均51000，分别0.86980516/37成功、0.73023952/31成功；BONES9000为0.78952191、16631/17301，LAFAN保持10/40、0.35465644。三个训练tmux正常退出，不重复启动或延长P8。
- P7已完成训练、正式评分、关键证据和轻量发布。continuation C42000为0.85912099、36/40、完成96.6163%、起身4/6、末三均值0.84328782与共同成功33；fresh F9000为0.52562120、20/40、起身0/6，约10h内未达0.82。源状态与比较见results/20261105-p7-feedback-reproduction-s0。续训33/40动作回报提高，主要新增损失集中两条起身；不能概括成整体精度持续退化。
- P6已完成训练、正式评分和轻量发布。B33000回报0.86624655、37/40、完成99.0832%，保留父34条全部成功；5/9节点和末三均值0.837913超过论文LAFAN评估0.82参照。父/A/B共同完整31条XY为2.0013/2.0917/0.0640m，已解决主要位置漂移。不要再将当前状态写成“未达到0.82”；也不把40/40当论文未给出的门槛。来源：results/20261105-p6-position-feedback-s0/summary.json、conclusion.md、review_20261105.json。
- P5 20261104-p5-actor-stability-s0已完成训练、正式评估和轻量发布。A/B均24000：A 34/40、0.713134、起身6/6；B 34/40、0.755425、起身3/6，平均完成96.2842%，保留父32成功中的30条。P6已从B24000完成续训，A24000作为历史起身参考保留；P7主父改为P6 B33000。复核见results/20261104-p5-actor-stability-s0/review_20261105.json。
- P3 20261102-h32-bce-s0 已完成，status=completed、unpublished=[]。C0-9000保留辅助BCE达到29/40、回报0.615404、起身3/6；C1删除BCE为15/40、0.482603。父B6000为13/40、0.409124。继续有效C0，不重跑P3。
- P4本段已完成：9000→18000，新增9000次联合更新/10.198小时；最终32/40、回报0.706754、起身3/6、跑步4/4。2026-11-04 02:55轻量发布完成，原tmux正常退出；不重复启动或自动追加训练。大产物留服务器待用户备份，不授权阶段自动清理。
- 原文Eq.(1)没有要求BCE对预测状态detach；k8/H32是默认。不能把BCE回传直接称为错误，也不能称C1是作者原版。
- 当前研究问题是困难动作与能力保持，并行推进BONES规模训练；P7从零学习暴露的问题保留，P9不机械再跑相同fresh9000。51000轮不是收敛证据。Table A.5为320000轮、LR衰减250000轮，但LAFAN达到0.82的迭代数未公开，不盲跑320000。迭代比例不是复现完成百分比。

## 工作位置与连续执行

- 使用autodl-d57，主项目 /root/autodl-tmp/robot-repro/supermimic，source activate.sh。
- 使用现有独立.venv、依赖锁与G1资产；禁止setup、安装、升级、重建或清理正常工作环境。不得修改Conda base、MPC-RL、π0、π0.5及其他项目的源码、环境或任务。
- 必要工作树放在明确源码目录，不放入待清理缓存；保留已有工作树和Git/stash。
- 使用独立tmux。单个Codex交互窗口≤4小时，后台可跨窗口连续运行，交接不停止/重启训练、不重建replay、不重置LR。
- 允许共享现有GPU，不另设12GiB限制、不要求独占、不停止其他任务；记录实际共享条件和耗时。

## P10实施（计划已发布，尚未启动）

- campaign=20261108-p10-8k-hard-practice-s0；工作树 /root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice。两路full8k_control/full8k_hard_practice并行，稳定性与全库能力同步推进；效率专项后置，必要消除全库评分空转。
- 两路从P9 bones_full_lafan_survival/checkpoint_0009000.pt完整resume三网络、三Adam、sampler、已保存Torch/CUDA RNG、iteration9000、actor_updates8995及LR。保留survival_weighted并非宣布其LAFAN对照获胜；保留原Critic LAFAN60000效果锚点。本轮不切换Critic变体或重新网络迁移。
- 两路均8192真实环境、8192想象batch、WM10×4096，H32/k8、replay每环境1000、collect2/3、Critic5×4、713/.5、原奖励/终止/PD/随机化与LR日程不变，不自动涨LR或WM optimizer次数。各实际新进程必要填充64步一次，9001起全部联合更新，不重做5轮WM-only。
- 两路source仍LAFAN2048/BONES6144。control reset=LAFAN2048+全BONES6144；candidate reset=LAFAN2048+全BONES5120+固定hard1024。hard为configs/p10_hard_motion_set.json的639条Stunts或名称含flip/side_roll/cartwheel/handstand，按原source_clip_id映射联合库。general继续包含hard，不按策略失败增删数据。
- hard只是重叠reset stratum，不是第三source。共享已恢复的returns/memory，各池内条件归一化；record仍按两个source各更新一次memory EMA，不把hard加入原source循环重复更新。保持Gmax10与现有timeout处理。
- 每路9001–27000，新增18000联合更新，或新阶段累计40h先到；父历史约71.40335h单列。真实恢复累计先前用时，不重新获得40h。单Codex窗口≤4h，独立tmux跨窗口连续，不因交接重建活跃replay/LR。
- 两路引用P9同一底层CPU只读memmap及现有manifest，不复制约45.4GiB参考库、不重筛/重转/重pack；H32末端goal窗口43帧保持。先完成首路必要初始化和填充，进入正常循环立即接第二路，不做容量试跑。
- 全库正式评分为15000/21000/27000，LAFAN保持为12000/15000/18000/21000/24000/27000及实际终点；按iteration−9000排程，不能用全局%6000代替。父9000同权重评分复用，40h监测子集从全库同次评分提取。
- 全库评估按(reference_steps, original_source_clip_id)排序组批，默认1024，仍覆盖全部动作从0至原终止/自然末尾，输出恢复原ID顺序。各既有失败组保留原ID最小两条，最多8个133帧尾窗，使用有界候选，不因执行顺序变化改选样，不重跑父模型对拍。
- 训练/评分各Torch2线程，实际CPU统计最多12个单线程worker。GPU评分、指定WM小证据和Git发布共用 /root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock，总并发1，训练不占锁；不终止其他项目。
- 只补P10计划冻结的六个P9 full9000失败短窗同动作WM预测，用已有真实状态/action/context33，最多32步（handstand17），不运行新物理/扫描起点。正常训练顺带记录hard/其余BONES/LAFAN的collect、WM、Actor实际曝光、hard clip/bin覆盖和已有forward分组误差；每千轮最多4个已有selected样本补actual objective/raw/weighted/Smean。
- 比较固定终点/共同节点的全库R、hard技能、body-orientation/共同完整质量和LAFAN保持，不只报完整数或挑最佳点。全部BONES逐clip用CSV每1000条分片、schema只写一次，保留失败；小summary直接提供类别/固定技能与共同集合变化。
- 推代码、实际配置、完整轻量评分、指定小证据和结论后不在用户电脑归档。不Release、不tar、不自动阶段清理，不把用户自行备份列成研究完成步骤；大产物留服务器，原checkpoint滚动和里程碑保护不变。
- 禁止防御性编程及任何单元/mock/冒烟/导入/形状/哈希测试、恢复演练、无关扫描/benchmark/监控。遇到真实错误才针对修复。预算结束如实评分发布，不自动扩预算、改变配方或启动P11。

## P9实施（历史已完成，不重复执行）

- campaign=20261107-p9-critic-full-scale-s0；工作树 /root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale。稳定性与修正后的完整BONES训练同步，效率专项后置；细节以P9计划与协议为准。
- 两路LAFAN均从P8 H32-51000完整恢复三网络、三套Adam、sampler、已保存Torch/CUDA RNG、全局迭代与LR。control原Critic，survival_critic仅改变Critic存活权重；均51001–60000或累计本阶段16h，9000联合更新。713/.5、k8/H32、aux_bce、原奖励/终止/PD/采样不变。
- 加权用当前reward之前detach的S_t，保留首次终止transition；mean(S_t*(V-target)^2)除全rollout固定mean(S_t)，所有minibatch复用该分母。不加epsilon、硬概率阈值或value/target clip。论文Eq.(3)本身无权重，这是项目方法修正，正式控制成绩决定收益。
- 自然终点沿用frame+step+1>=lengths[clip]-1，不引入collector500步timeout作为想象终止。Actor目标和λ递推不改；正常同一次forward记录raw/weighted MSE及精确零S后缀贡献。
- 并行修正全BONES筛选：高处/穿透用non-world机器人body origin最低z；浮脚仍用foot geom-to-plane。补论文公开的外部支撑/地形名称条件，参考SONIC官方清单，保留翻转/侧滚等平地技能，不照搬上游难动作排除。
- 对全部原始metadata应用新规则，复用已有有效NPZ和CSV；只有新规则允许却无有效NPZ者补转换，包括之前名称/物理规则误排者。不重下载、不覆盖P8清单、不凑作者计数、不按策略失败过滤。冻结新的完整清单和约40h监测子集；监测统计从全库同次评分提取。
- 第三路bones_full_lafan_survival使用全部修正后BONES+LAFAN；同一H32-51000仅迁移三网络权重，新建Adam/联合sampler/replay/RNG/阶段计数，H32+存活加权Critic，1–9000或累计16h，前5轮WM-only。记录继承约57.8705h成本，不称从零。
- 4096环境固定1024 LAFAN/3072 BONES，每来源内保持原50/40/10 reset分布；记录实际WM/Actor样本份额。25%为本轮明确研究选择，不伪称作者默认，不增加配比扫描。
- 完整库参考保留CPU连续数组/只读memmap，按阶段取GPU窗口。H32+goal10需43帧，4096 batch约170MiB；参考可预取，goal仍逐步用预测root quaternion在GPU可微构造。完整评分也用CPU参考，避免另复制全库显存；纯LAFAN两路保留现有读取语义。
- LAFAN两路每1000轮全40评分，父37成功，固定末三58000/59000/60000。第三路更新前checkpoint0及3000/6000/9000、实际终点全BONES评分；3000/6000/9000和实际终点评LAFAN保持，0点复用同权重父评分。两种评分都显式选择source子库并分别报分，训练同数据resume约束保留。
- 只从已保存轨迹补H16-50000 dance1_subject1 104.50–107.14s和H32-49000 fallAndGetUp1_subject1 6.70–9.34s两个成功窗；对应失败窗复用。每千轮正常rollout最多4条，并计真实reset/WM有效窗/Actor起点的来源及剩余步分组，不新增模型/物理推理、扫描或测试。
- 先启动两路最小Critic对照，同时16个单线程CPU worker准备修正数据；全库就绪立即接第三GPU任务，不等对照胜负。每训练/评分Torch2线程，25vCPU下预处理默认16、纯数据无评分可20。
- 三路独立tmux/run/log，目标96GB GPU并发3训练。正式评分、指定GPU证据、Git发布共用 /root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock，总并发1，训练不占锁。窗口≤4h，后台继续；活跃replay/LR不重启，实际恢复累计旧预算。
- 发布完整逐clip标量按2000条紧凑CSV/JSONL分片，附小summary/字段/索引、实际配置、筛选原因、紧凑统计及指定小数组。BONES终点≤8失败尾窗按预定flip/side_roll/地面起身滚动/其余各2名额，从同次评分缓冲取得。
- 大产物留服务器；不Release、不打tar、不在用户电脑归档、不自动清理。禁止防御性编程与单元/mock/冒烟/导入/形状/哈希测试等无关工作。预算结束交付真实结果，不自动扩预算、改采样器、加H/PPO/多seed/实机或开P10。

## P8实施（历史已完成，不重复执行）

- 用户顺序：稳定性与大规模训练同步推进，效率优化后置。campaign=20261106-p8-stability-scale-s0，工作树 /root/autodl-tmp/robot-repro/supermimic-p8-stability-scale；完整细节按P8计划和协议。P1–P7以下为历史约定，不重复执行，也不让旧阶段范围禁止覆盖本次明确授权。
- 两路LAFAN正式联合训练都从P7 continuation C42000完整恢复网络、三套Adam、sampler、已保存Torch/CUDA RNG与全局LR；A保持H32，B仅H16。各42001–51000、9000联合更新或累计新阶段16h上限。父基线为36成功/4失败，B33000的37条是历史锚点。
- 保持713根XYZ反馈/.3m、Actor LR scale=.5、k8、aux_bce、analytic_smooth .05、4096真实与想象batch、原奖励/物理终止/PD/采样/随机化。H16可能更依赖Critic并掩盖后段真实风险，以全动作控制成绩判断，不按想象目标大小选方案。
- 每路初始replay64步；活跃tmux跨窗口继续，不重建replay/LR。进程实际退出后，从未保存replay的checkpoint恢复才作一次必要填充，记录真实恢复并累计已消耗P8预算，不重新获得16h，也不做恢复演练。源47.1454h不扣本阶段上限。
- 两路每1000轮全40正式评分，43000–51000，末三49000/50000/51000；时间先到发布真实终点。报告全部逐动作指标、父36保持、四个父失败演变、起身/跑步和尾三交集；共同更新节点比较，不拼接各checkpoint成功并集或只挑最佳点。
- 同时取BONES官方G1归档和实际metadata，复用已有合法HF访问；若门控未获准，报告具体官网要求，其他工作继续。实际CSV时标/列定义不能照搬LAFAN。按论文公开过滤条件及明确冻结的项目门控处理，CPU默认16个单线程worker，第三路未启动且无评分时可20。
- 冻结约40h完整可行动作子集后立即接第三GPU训练；其余完整库转换继续保存在独立目录，不能变更活跃manifest。第三路bones40_transfer_h32只加载C42000三网络权重，新建optimizer/BONES sampler/replay/RNG/阶段计数，H32、1–9000或累计16h，5次WM-only后联合更新。记录全部预训练沿革，不称从零3h复现。
- 第三路更新前保存BONES定义的checkpoint0并全子集评分，3000/6000/9000及实际终点完整评分；终点一次显式跨数据LAFAN保持评分，分别记录训练/评估定义，原同数据resume语义保留。BONES实际N和逐clip等权归一化，参考N_i帧的分母为0.1*(N_i-1)，不能用40或训练500步截断。
- 必要适配限于数据配置/实际N、clip及reset-bin前缀和、有界参考加载、分批完整评分与在线标量、metadata类别、明确weights_transfer和三job轻量调度。40h参考驻第三路GPU，全264h不与三路同时装显存；不做泛用框架或纯吞吐benchmark。
- 补两组已有异常38089/41379各4条、共8条32步同动作物理对照，恢复记录context到实际摩擦/COM参数；C42000四个实际失败各补失败前64/32步起点的H32同动作WM窗，共8窗，复用真实轨迹。正常训练仅存已有统计与每千轮最多4条已算异常样本，不新增forward/backward、梯度扫描。
- 目标三个GPU训练进程并行，每路Torch2线程；所有正式评分、固定GPU短证据和Git发布共用唯一锁 /root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock，总并发1，训练不占锁。各自独立run/tmux/log，依实际共享显存接第三路，不停其他项目。单Codex窗口≤4h，后台连续运行。
- 发布全部逐动作评分、实际配置、manifest/过滤统计、紧凑训练统计、计划指定小NPZ/JSON、来源和真实结论。BONES最多8条失败尾窗从同次正式终点评分的有界缓冲取得，不额外全动作重放。大产物留服务器，不Release、不打tar、不在用户电脑归档、不自动阶段清理。
- 不增PPO、多seed、更多H扫描或实机；不放宽成功标准、不再改LR/reward/终止、不将Critic夹到[0,10]。固定预算结束先交付，不自动延长或开P9。禁止防御性编程与各类无关测试的约定继续生效。

## P7实施（历史已完成，不重复执行）

- 一个源码工作树 /root/autodl-tmp/robot-repro/supermimic-p7-reproduction；campaign=20261105-p7-feedback-reproduction-s0。两个任务共享713/.5有效配方，研究不同问题，不作同初始化A/B胜负比较。
- continuation从P6 root_position_feedback B33000恢复完整网络、三套Adam、sampler、已保存Torch/CUDA RNG与全局LR，33001–42000，新增9000联合更新。父基线37/3，复用已发布评分；713自身恢复不重复扩列。
- from_scratch全部新初始化，seed0，无父checkpoint、不传resume、不继承网络/Adam/sampler/RNG与旧时间；713全部输入按正常初始化，不执行710→713迁移。全局1–9000，前5次原有WM-only，之后8995次Actor更新；LR从1开始。
- 各自初始64步replay只填一次，新训练阶段各16小时上限，评估/发布另计；不自动扩预算或开P8。固定k8/H32、aux_bce、4096环境、公共goal710、Actor713及XYZ/.3、半ActorLR、原WM/Critic日程、奖励/物理终止/PD/采样/随机化。
- 两路GPU正式训练并行、独立run/tmux/log，每进程Torch2线程；正式评估、指定六个WM短窗预测与Git发布共享work/p2-publication.lock总并发1。最多4个CPU进程只读取计划指定的既有数据。按P6实测预计约10–12小时训练；单Codex窗口≤4小时，后台跨窗口继续，不重启replay/LR。
- 每1000轮正式全40评估。continuation节点34000–42000，尾三40000/41000/42000，报告父37保持；fresh节点1000–9000，尾三7000/8000/9000，报告首次观测到≥.82节点及从零成本，不伪造父保持率。时间先到则发布真实非整千终点。
- 必要适配：薄双job启动/收尾；P7纳入现有紧凑发布；按job显式处理有父/无父、区间起点、fresh previous_elapsed_seconds=0和产物路径；fresh前5轮训练统计不读取不存在的Actor字段，不补零；failure_windows覆盖实际所有失败；mean根位置误差不误称before_failure；comparison不反复复制每动作reward明细。
- 并行补P6证据，不阻塞训练：三个B33000失败与同支成功对照共5个2.64秒物理窗、仅B33000的六个H32同动作WM预测、B31四个主要回撤与B30成功对照共8窗、30001–31000已有日志两个明确极值各±10行。精确时间、动作/状态对齐、来源及输出字段按P7计划，不新物理回放，不重复25k→26k报告。
- 正常训练只复用现有张量记录Eq2奖励/末端bootstrap、V/λtarget极值与survival；主续训每千轮仅保留最大Critic MSE更新中≤4条最大|λtarget−旧V|样本，从零只保留标量。不新增forward/backward、梯度扫描、参数全量复制、RNG采样或更新干预。
- 用户本轮授权分析所需少量短证据数组进Git，按下节执行；完整大产物仍留服务器。P7文档发布不代表运行适配或训练已经完成；实际启动/结束时同步真实状态。

## P6实施（历史已完成，以下保留原执行约定，不作为P7启动指令）

- 一个P6源码工作树 /root/autodl-tmp/robot-repro/supermimic-p6-position-feedback。两支从P5 B24000恢复完整网络/三套Adam/sampler/Torch及CUDA RNG，各初始填充一次64步replay；全局24001–33000，每支新增9000联合更新、新阶段各16小时上限，旧累计耗时不用作预算，正式评估/发布另计。
- A no_position_feedback原710维；B root_position_feedback仅给Actor encoder追加当前相对根XYZ三维到713。两支Actor LR scale都为0.5；WM/Critic原日程。误差=完整机器人根旋转逆*(当前参考根位置−当前机器人根位置)/0.3；不改公共goal710或Critic已有privileged相对位姿。
- 真实collection、每一步imagined state及正式evaluate使用同一特征定义。想象中当前误差不detach，不固定为rollout起点。history930、latent32、其他网络层、WM/replay、k8/H32、aux_bce、原奖励/终止/PD/采样器/随机化均保持；始终完整联合更新。
- 仅反馈支首次710→713恢复时，encoder.0.weight保留旧列、追加3列零；对应Actor Adam exp_avg/exp_avg_sq同步扩零列，保留step和其他状态。713自身恢复不重复扩列，不重置整个Actor或Adam。该输入是本项目假设，不是已公开的作者goal定义。
- 两路GPU训练尽可能并行，独立run/tmux/log；共享work/p2-publication.lock使正式评估和Git发布总并发1。每训练/评估进程Torch 2线程，最多4个有具体问题的CPU轨迹分析进程。P5实测支持预计约10–12小时训练墙钟，16小时是上限，评估/发布另计；不增开无关实验或benchmark。
- 必要适配是Actor输入/三条调用路径/有限checkpoint迁移、两份继承配置、薄P6启动收尾及现有轻量发布。publish_checkpoint当前精确匹配P5协议，P6必须复用多arm紧凑分支，不能退回累计metrics.jsonl/单summary。父评分用B24000实际34成功/6失败，节点25000–33000，尾三31000/32000/33000，不沿用P5硬编码。
- 每1000轮正式全40评估；固定33000与末三节点比较，时限先到发布真实非整千终点并说明进度差。报告全部回报/完成、父34保持、起身/跑步身份、成功交集、奖励项贡献及1−R=(1−C)+(C−R)。XY公平比较取父B24000/A最终/B最终共同完整成功集合，同时保留全40数据。不挑最高节点、不拼接动作。
- 位置反馈的主要判断是root-position奖励和共同完整集合XY能否改善，同时看总体回报/覆盖/保持。只补P5缺失尾部的条件上界0.792583低于0.82，说明执行段质量也须提高，不是未来策略上限。一次过0.82不等于整篇论文效率/规模/实机已复现。
- 只在已有JSON不足以回答时间演变时并行读P5保存NPZ：三个大漂移动作、dance1_subject1翻转、B三个失败起身对A24000成功轨迹。复用已完成P4分析，不重仿真、不扫描起点、不阻塞训练；P5没有新的同动作WM展开，不能将P4旧误差当当前B误差。
- 阶段结束先推关键结果和真实结论，不自动延长、增seed、改H/k/BCE/reward/终止、开BONES/实机或P7。单窗口≤4小时，后台跨窗口继续，不重启replay/LR。以下P5/P4仅为历史，不重复执行。

## P5实施（历史已完成，不重复执行）

P5两支均已完成到24000；本节保留原方案供溯源，当前执行入口为P10。

- 从同一C0-18000恢复两支完整联合训练：A c0_control保持原设置；B actor_half_lr只给Actor学习率乘0.5。两组各新增6000次更新到24000，各自新训练阶段上限16小时，含一次64步replay填充；正式评估和轻量发布另计，不自动追加预算。
- 在每轮set_schedule应用actor_learning_rate_scale=1.0/0.5；WM/Critic保持原基础LR和全局余弦日程，恢复Adam/sampler/RNG，不重置迭代。不能只改初始化LR，也不能把公共learning_rate减半。完整执行真实采样→WM拟合→Actor/Critic。
- 保持k8/H32、aux_bce、analytic_smooth温度0.05、robot_root710维、4096环境、原奖励/物理终止/PD/采样器/噪声/随机化。半Actor学习率是待检验的研究假设，不是已证实根因或论文默认。
- 使用同一P5源码工作树、独立run/tmux/log；尽可能并行两支GPU训练，正式评估与Git发布通过同一work/p2-publication.lock总并发1。各训练/评估保持Torch 2线程，CPU既有轨迹阅读最多4进程，不为占满96GB/25核增开无关实验。
- 必要适配限于独立Actor LR、两份继承配置、薄P5启动/收尾和发布。旧P4发布固定9000/29/11及单run summary，P5必须用18000父评分动态计算32成功/8失败，并按arm隔离汇总。复用已有评估和统计，不能原样执行旧P3/P4收尾main。
- 每1000新增轮完整评估40动作，保留19000至24000全部节点；时间先到则发布真实非整千终点。固定终点和末三共同节点比较回报、动作身份/父32保持、三节点成功交集及起身，不能只挑最佳checkpoint。最终XY只比较18000/A/B都完整成功的同一集合并注明范围。
- 并行只读已有评分轨迹：dance1_subject1固定约107s失败，以及三个最终失败起身对应的12000/14000成功轨迹。不重放旧checkpoint、不扫描额外起点；关键证据见P5计划。
- 发布改为完整40动作评分JSON、每1000轮紧凑训练统计、必要失败证据与结论；不再每节点重复推累计metrics.jsonl。完整逐轮日志留服务器。文档发布不代表这些执行端适配已完成。
- 不自动增加H16、k16、XYZ、BCE变体、PPO、多seed、BONES或实机；阶段结束先交付真实结论和关键结果，不自动开下一轮。

## P4实施（历史已完成，不重复执行）

- 一个新run，从C0-9000完整网络/优化器/sampler/Torch及CUDA RNG继续，新增9000联合更新，全局9001–18000。新训练阶段上限12小时，含一次64步replay预热；旧累计耗时单列，结束正式评估与轻量结果发布另计。预计约9.7小时，时间到的非整千最终节点也发布。
- P4已恢复C0-9000父权重与LAFAN40工作数据，复用当前输入，不重复恢复/预热、不重跑retarget或父版本全量评估。历史Release来源保留在协议中。
- 从C0实际config继承，仅修改run/续训来源、max_iterations=18000与max_hours=12。保持robot_root、目标710维、H32、k8、aux_bce、analytic_smooth温度0.05、4096环境、原state表示/缩放/70维mean、网络、reward、物理终止、PD、采样器、噪声/随机化、optimizer及全局LR日程。
- 始终完整执行真实采样→WM拟合→Actor/Critic。已有核心路径没有找到需先修的确定算法错误，不制造新模块改动。
- P4单run已启动；本次只调整下节所列发布/收尾入口，不重复单run启动适配。最终状态如实区分训练、正式评估和轻量发布；大产物待用户备份不阻塞研究完成。
- 每1000新增轮（10000–18000）完整评估40条原动作；按完整时长归一化回报和原高度/倾斜终止判断。最终评分与分析共用真实轨迹；需要视频时复用该轨迹，不让批量渲染阻塞结果推送，不拼接逐动作最佳checkpoint。
- 报告6条起身、4条跑步、原11条失败与已成功动作保持；区分早期失败和末尾失败，持续观察米级XY漂移。coverage是额外诊断，不是论文成功率；当前结果是训练动作覆盖，不是未见动作泛化。
- 继续已有类别采样/失败/reset、全局WM分项误差和计时记录；现有日志没有按类别的WM误差，不能混写。只分析真实最终失败的跑步/起身尾窗，不再做双模型全套对照。
- 同动作预测的predicted_failure_probability来自预测状态代入analytic_smooth，不是learned BCE head或closed-loop轨迹。低训练MSE不等于更好控制，不把辅助BCE获胜包装成唯一机制已证明。
- 不自动启动C1复跑、BCE权重/detach、H16、XYZ、state loss乘70、PPO、更多seed、BONES或实机。若后续真实训练停滞，再由已有结果选择一个具体问题。

## 禁止无关工作

- 禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、通用fallback/监控框架及无关报告。
- 不另开benchmark、不机械120起点扫描、不重复旧checkpoint全量回放；遇到真实运行错误才针对定位修复。
- 不把论文未公开的goal/state缩放/解析终止细节伪称作者源码，不通过放宽成功标准制造成绩。

## 轻量发布与用户管理备份（最新约定，覆盖旧上传/清理要求）

- 顺序：训练/正式评估完成 → 先推代码、配置、完整逐动作/逐回合评分（BONES使用紧凑CSV/JSONL分片）、关键训练区间统计与结论 → 继续既定研究。按节点批量提交；完整逐轮metrics.jsonl和大日志留服务器，不每节点重复上传累计日志。
- Git保存LAFAN完整40动作及BONES全部选定动作的逐clip评分、关键失败窗口、紧凑曲线/统计及现有运行索引；保留失败结果。用户授权补传分析所需数据：按当前P10计划指定的小型WM/失败窗NPZ/JSON与正常rollout样本可以进入Git，旧P8证据保留，附来源、context、数据定义与数组语义；不把完整逐帧数组改成全量JSON上传。P7已发布证据保留。
- 大checkpoint、完整视频、完整原始轨迹/数组、数据缓存、大日志默认留服务器，不上传GitHub Release、不加入全量后台上传队列、不为上传打tar、不在用户电脑另做归档。需要分享个别大文件时由用户另行安排。
- 研究交接不等待大文件上传、视频批量渲染或用户备份。原始评分轨迹和研究必需数据仍保存；必要视频从同一真实轨迹按需生成。
- 用户定期从服务器数据盘导出到自己的存储盘备份，并由用户统一删除阶段产物。取消此前“上传完成后自动清理服务器副本”的授权；Git/Release已存在副本或用户已备份均不自动授权程序删除。
- 训练器每轮保存与最近20轮滚动保留规则照旧，父版本/整千/最终/续训所需checkpoint保留；不把滚动淘汰扩展为阶段结束批量清理。
- 在现有summary/索引记run、iteration、父checkpoint、服务器产物路径/用途、仍在使用的文件及用户备份状态；未获用户确认不标已备份。不新增归档系统、看板、哈希、重下载核验、恢复演练或全盘扫描。
- 后续续训使用服务器或用户备份中的实际checkpoint路径，不假设新版本都有Release下载链接。凭据、SSH私钥、代理配置不入Git。
- P4实际发布/收尾入口已于2026-11-03 22:15接入轻量策略：正式评估后推Git，默认不打包/上传大产物，收尾无阶段/输入副本删除和批量渲染。原训练PID149031已于18000轮正常结束；整千节点从14000起使用新入口，保留历史Release，不重做已完成节点。
- 将最新约定同步到实际工作树，保留未提交改动；只处理独立发布/上传任务，不能终止训练/评估父进程。仅推送文档不代表服务器运行逻辑已切换，实际接入状态如实记录。
- 保留产物留服务器待用户备份是正常结果，不把它们列为必须补传才能完成研究的失败项。阶段收尾报告真实成绩、轻量GitHub链接和本地产物位置，不自动删除或重新归档。
- 永久保护源码、scripts/configs/docs、.git/stash、.venv、依赖锁、激活脚本、G1 XML/网格、开发工作树、仍在使用的输入/父模型、其他项目和共享依赖。
- 禁止删除项目根、整个outputs/.cache/work，禁止旧finish或20261101整体清理入口删除保留实验原件。P3已完成的历史清理不重做。
