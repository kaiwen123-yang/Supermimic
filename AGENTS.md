# SuperMimic 执行约定

本仓库是用户的独立论文复现项目，远端为 https://github.com/kaiwen123-yang/Supermimic 。

## 复现验收标准（用户最新确认）

用户确认验收标准（2026-11-05）：**达到作者对应实验的指标，就算该项复现成功。当前LAFAN1全40正式评估回报目标0.82，P6 B33000为0.86624655，因此已认定LAFAN1指标复现成功。** P7属于达标后的巩固与研究，不是复现成功的前置条件；不追加40/40、从零重训、更多seed、H100同等耗时、BONES或实机等验收要求。已保存B33000的达标结论不因后续研究节点回撤而撤销。

## 当前任务与证据

- **当前主线O3：官方BONES稳定性方案已发布，尚未执行（plan_published_not_started）。** 入口为docs/O3_OFFICIAL_BONES_STABILITY_PLAN.md、configs/o3_official_bones_stability_protocol.json和docs/O3_CODEX_START_PROMPT.md。本次仅发布O2复核、下一段方案/协议/启动词；尚未实施O3运行适配、连接D57或启动训练。两路从O2同一3h权重热启动，原LR2e-4与统一0.25倍LR5e-5比较；各4096环境、新增最多32000次联合更新，共享整个campaign最多8h训练墙钟。O1/P6成果保留，P12继续暂停。
- **O2已完成并复核。** BONES-only 130394条、seed0从零、4096环境；3h R=.93501955、130215条完整，6h R=.87472977、129997条完整，12h实际final R=.62929250、83910条完整。LAFAN跨库完整数25/26/0。3h作为良好主锚点，6h作为困难覆盖参照；后期回撤不撤销3h成绩。详见docs/O2_REVIEW_20261112.md及results/20261111-o2-official-bones-s0/summary.json。历史tmux sm-o2-official-bones-s0已结束，不重启、不追加O2预算；latest_training的evaluation_pending是训练退出快照，全部评分与轻量发布已完成。
- **O1历史首段已完成并复核。** seed0从零训练，首个正式3h节点R=0.85882311、39/40；实际终点约3h8m17s，R=0.87443989、40/40，因formal_return_target_reached停止。全40的XY时间均值0.765250m、9条>=1m，完整执行与精确全局跟踪分开报告。复核见docs/O1_REVIEW_20261111.md及results/20261111-o1-official-lafan40-s0/review_20261111.json，当前完成状态见summary.json。D57工作区supermimic-official-workspace，历史tmux sm-o1-official-lafan40-s0；官方源码abc124c、作者研究库dd51a9f。latest_training的evaluation_pending是退出快照，final已完成。不重跑O1、不补6h/12h或追加O1预算。O2亦已完成，新阶段按顶部O3独立方案接续；既有LAFAN验收成果和其他任务保留。
- **P11最新结论：** 两路均36000，原残差全BONES R=.86375135、129152/130394完整、hard312/639；高度约束R=.85693786、129598完整、hard305/639。候选多446条完整主要来自普通动作，回报及同输入WM误差较差；两路flip0/44、handstand0/160，LAFAN终点均29/40。候选在部分中间节点与LAFAN跨节点保持有优势，不称全面退化。当前原WM在仍存活的倒立第16步高度已低估.100342m（S=.997672），与旧P9飘高诊断不同。合法k8起点bin全部得到WM曝光，66个零起点bin均为参考自然末尾不足8步，不能说关键开头未进learner。来源见本轮复核及review_20261111.json。
- **P11两路训练、评分、固定证据与轻量发布已完成。** 启动核实时间 2026-11-10T11:23:31.198241+08:00；实际状态见results/20261110-p11-root-height-consistency-s0/summary.json。两路已按各自真实预算终点完成，不重复启动P10/P11或自动追加预算。两路同P10 hard27000完整resume，仅比较root-z残差与同次预测速度梯形高度；各8192/8192/WM10×4096，原hard配额，新增9000联合更新或累计20h，到36000；全BONES/LAFAN节点30000/33000/36000及实际终点。父七窗224步预测已完成，终点两WM各同输入一次。
- P10两路已于2026-11-10完成训练、全部正式评分、指定证据与轻量发布，均27000、各新增18000联合更新。control全BONES R=0.86659060、129579/130394、hard193/639、LAFAN0.81479628/36完整/起身5；candidate全BONES R=0.85921480、129516/130394、hard298/639、LAFAN0.78821171/33完整/起身3。candidate侧滚21/22、侧手翻85/120，但flip0/44、handstand0/160。结果见results/20261108-p10-8k-hard-practice-s0/summary.json、conclusion.md和paired_comparison.json。两个训练tmux正常结束；不重复启动或追加P10预算。P11也已完成；当前新增工作以顶部O3方案及启动词为准。
- P9三路训练、全部正式评分与轻量发布均已完成。LAFAN原Critic60000为0.89043870/38完整，加权为0.84312458/36；全库9000为0.84379710、129220/130394，264.430633h，LAFAN保持29/40且起身0/6。复核见docs/P9_REVIEW_20261108.md及results/20261107-p9-critic-full-scale-s0/review_20261108.json，实际完成状态见该campaign的summary.json。
- P8已经全部完成：results/20261106-p8-stability-scale-s0/summary.json、conclusion.md。H32/H16均51000，分别0.86980516/37成功、0.73023952/31成功；BONES9000为0.78952191、16631/17301，LAFAN保持10/40、0.35465644。三个训练tmux正常退出，不重复启动或延长P8。
- P7已完成训练、正式评分、关键证据和轻量发布。continuation C42000为0.85912099、36/40、完成96.6163%、起身4/6、末三均值0.84328782与共同成功33；fresh F9000为0.52562120、20/40、起身0/6，约10h内未达0.82。源状态与比较见results/20261105-p7-feedback-reproduction-s0。续训33/40动作回报提高，主要新增损失集中两条起身；不能概括成整体精度持续退化。
- P6已完成训练、正式评分和轻量发布。B33000回报0.86624655、37/40、完成99.0832%，保留父34条全部成功；5/9节点和末三均值0.837913超过论文LAFAN评估0.82参照。父/A/B共同完整31条XY为2.0013/2.0917/0.0640m，已解决主要位置漂移。不要再将当前状态写成“未达到0.82”；也不把40/40当论文未给出的门槛。来源：results/20261105-p6-position-feedback-s0/summary.json、conclusion.md、review_20261105.json。
- P5 20261104-p5-actor-stability-s0已完成训练、正式评估和轻量发布。A/B均24000：A 34/40、0.713134、起身6/6；B 34/40、0.755425、起身3/6，平均完成96.2842%，保留父32成功中的30条。P6已从B24000完成续训，A24000作为历史起身参考保留；P7主父改为P6 B33000。复核见results/20261104-p5-actor-stability-s0/review_20261105.json。
- P3 20261102-h32-bce-s0 已完成，status=completed、unpublished=[]。C0-9000保留辅助BCE达到29/40、回报0.615404、起身3/6；C1删除BCE为15/40、0.482603。父B6000为13/40、0.409124。继续有效C0，不重跑P3。
- P4本段已完成：9000→18000，新增9000次联合更新/10.198小时；最终32/40、回报0.706754、起身3/6、跑步4/4。2026-11-04 02:55轻量发布完成，原tmux正常退出；不重复启动或自动追加训练。大产物留服务器待用户备份，不授权阶段自动清理。
- 原文Eq.(1)没有要求BCE对预测状态detach；k8/H32是默认。不能把BCE回传直接称为错误，也不能称C1是作者原版。
- 独立实现历史研究问题包括困难动作与能力保持；O2官方BONES-only从零训练已完成，当前新增方案为O3同父权重固定学习率比较，LAFAN仍只作跨库评分。P7从零学习暴露的问题保留，P9不机械再跑相同fresh9000。51000轮不是收敛证据。Table A.5为320000轮、LR衰减250000轮，但LAFAN达到0.82的迭代数未公开，不盲跑320000。迭代比例不是复现完成百分比。

## 2026-11-11 专项存储迁移（仅明确调用本任务时执行）

- 用户本轮明确授权将 Supermimic 原始/过程数据分类导出到本机 H:\Supermimic；确认本地转移成功后，删除不再依赖的对应服务器文件。执行说明见 docs/STORAGE_EXPORT_TO_H_20261111.md，本机目录脚本见 scripts/init_supermimic_archive.ps1。
- 此次专项授权覆盖旧阶段的日常“不自动归档/清理”默认限制，无需重复询问是否开始。但不会把迁移挂到 P12 收尾或变成今后每轮实验的固定步骤。
- 已结束且不再使用的过程文件按冻结清单分批归档、下载并本机确认后精确删除；当前/下一轮工作数据、父模型、复现验收和研究参照只备份并保留服务器原路径。活动 run 整体延后。
- 保留 P12 父 P11 residual36000、已有保护节点、P9共享memmap及真实底层文件、LAFAN工作数据、P10固定尾窗/P11父证据、环境/G1/源码/Git/stash、发布锁及其他项目。不得按旧阶段名整工作树或整个 outputs 删除。
- 执行端必须能访问实际 H 盘与 D57；本次发布仅准备说明，尚未打包/传输/删除。只在本机确认归档完整读取、字节数匹配后，删除未变化且未再启用的明确源文件。
- 小批次、低优先级、单线程压缩和一条传输连接；迁移不占 GPU，不长期持有训练发布锁，不让训练等待迁移。该存储任务本身不启动下一轮训练；已由其他会话启动的训练照常继续。
- 不新增哈希/冒烟/模型恢复/benchmark等测试或防御性框架，不安装重建环境，不自动删除 H 盘归档。用户未来决定本地归档的保留时间。

## 工作位置与连续执行

- 使用autodl-d57，主项目 /root/autodl-tmp/robot-repro/supermimic，source activate.sh。
- 使用现有独立.venv、依赖锁与G1资产；禁止setup、安装、升级、重建或清理正常工作环境。不得修改Conda base、MPC-RL、π0、π0.5及其他项目的源码、环境或任务。
- 必要工作树放在明确源码目录，不放入待清理缓存；保留已有工作树和Git/stash。
- 使用独立tmux。单个Codex交互窗口≤4小时，后台可跨窗口连续运行，交接不停止/重启训练、不重建replay、不重置LR。
- 允许共享现有GPU，不另设12GiB限制、不要求独占、不停止其他任务；记录实际共享条件和耗时。

## O3官方BONES稳定性（方案已发布，尚未执行）

- campaign=20261112-o3-official-bones-lr-s0；run为o3-bones-lr-control-s0和o3-bones-lr-quarter-s0。当前仅发布方案、协议与启动词，O3运行适配尚待执行端实施，未启动服务器训练。执行端收到docs/O3_CODEX_START_PROMPT.md后按其范围完成必要适配和正式运行，不重跑O2或独立实现旧阶段。
- 共用O2 hour_03的/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o2-official-bones-s0/checkpoints/checkpoint_000079816.pt；恢复同一WM/Actor/Critic及normalizer/sim-context bundle，两路按相同规则新建optimizer、replay、sampler和随机状态。明确weights warm-start、full_resume=false，父31924联合更新和本段新增计数分开；旧O2 6h不是严格匹配control。保护3h、6h和全部历史节点。
- 唯一比较为三网络固定LR统一倍率：control2e-4、quarter5e-5；构建learner前设置，保持官方Muon/Adam分配和capture路径。各4096真实环境，WM10×2048/窗口8、Actor4096/H32、GenCoord/proprio/history10；数据、奖励、终止、DR、采样及其余参数不变。当前Muon的float LR在CUDA graph捕获后固定，不仅套Python scheduler；不把本次0.25倍干预称论文Adam+cosine的精确复原。
- 两路优先并行，各新增最多32000次联合更新；整个campaign共享最多28800秒训练墙钟，从driver启动首个正式训练child之前计时，包含初始化、争用和实际中断，不是每路各8h，也不因交接/错误恢复重置。固定新增8000/16000/32000及实际final只保存；比较双方实际存在的共同更新节点，不将不等更新量final当配对。单Codex交互≤4h，tmux可跨窗口连续。
- 等全部训练child真正退出后，单个BONES worker装库一次，依次评两路所有实际固定节点；该worker退出后再由40-env worker评对应LAFAN节点。复用O2已完成packed数据与评分口径；评分和发布共用既有p2-publication.lock、并发1。训练和评分Torch各2线程，CPU元数据/汇总最多12个单线程worker；正常运行记录资源，不新增容量benchmark或停止他人任务。
- 全量逐clip、固定hard/non-hard、共同完整质量和训练计数按方案发布。结果只支持本seed同一热启动方案的局部对照；低LR有效不证明O2唯一根因或跨seed稳定。R>.90及作者25失败分别报告，成员未对齐不凑数。保留既有O1/P6成功，P12暂缓；本段不新增演示/视频、完整恢复框架、参数搜索或阶段归档/清理，到预算如实交付。

## O2官方BONES（历史已完成，不重复执行）

- O2的训练、全部正式评分和轻量发布均已完成；以下保留原运行设置供溯源，不作为重启指令。状态以campaign summary及docs/O2_REVIEW_20261112.md为准。新阶段范围由上方O3方案和独立启动词给出，O1不重跑，P12暂缓。
- campaign=20261111-o2-official-bones-s0；run=o2-official-bones-s0；tmux=sm-o2-official-bones-s0。复用/root/autodl-tmp/robot-repro/supermimic-official-workspace及其既有独立环境，固定HybridRobotics/supermimic@abc124c1bd5976341034668af3d12c087f2f1f55和HybridRobotics/mjlab_research@dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。不重新setup、安装、下载、retarget或恢复全量逐clip NPZ。
- BONES-only 130394条，seed0从零初始化WM/Actor/Critic，不加载O1权重或声称full resume。单卡4096真实环境，WM每次10×2048、horizon配置8；Actor batch4096、H32，proprio/history10。保留官方学习算法、奖励、终止、采样与日程；不加入LAFAN配额、旧hard quota、713维反馈、BCE、存活加权Critic或P11高度约束。
- 数据沿用保留的P9连续store及manifest，从qpos/qvel按O1关节与坐标映射分块生成官方六字段packed目录；combined源offset441140映射到packed0，BONES共47727908帧。约12.624GiB为六字段float32静态参考，不是总训练显存。使用作者已有packed loader，不重写训练loader、不任意删除880条以凑作者129514条。
- 首段累计训练上限12h（43200s）或1000000 collection steps，先到者停止；这是本计划选择的有限预算，不是论文训练要求或达标耗时承诺。3h、6h及实际final只保存checkpoint，不在活跃训练期间启动GPU评分。O2不按回报早停，不沿用O1的R>=.82停止条件；R=.90仅为SONIC参照，作者25条失败为其不同成员集合上的参考结果。
- 必须等训练子进程实际退出后，单个BONES评分worker以4096环境装库一次，顺序评估3h/6h/final已保存节点；按长度排序为32批，最后一批3418条有效，其余padding保持inactive。该worker退出后再评分同3节点的LAFAN40。若步数上限先到使某时间节点未产生，按实际保存节点如实交付，不补训伪造节点。GPU评分与发布沿用/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock，并发1；CPU元数据和文档工作可并行，训练仅1路。
- LAFAN结果称跨库评分；本轮从零且只训练BONES，不称O1遗忘/能力保持，也不称严格未见动作泛化。完整逐clip成绩、真实配置、来源与紧凑统计进入Git；大产物留服务器，沿用原保护与轻量发布约定。完成本段后交付实际结果，不自动扩预算、增加seed/对照或启动P12。

## O1官方复现（历史首段已完成）

- 初始比较固定用户dd28b969e7ab33a3e285f2caa7469e745f7cb5a0与官方5efbf114e11f725c31d83e217be987c13c0e4ce2；完成复核固定用户2b44fa32587e1a68be8b9d4de61485cd267e29c8及实际官方abc124c1bd5976341034668af3d12c087f2f1f55/研究库dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。原论文v1与最新v2核心公式和实验附录未实质变化。当前main的Muon、LayerNorm/GELU等后续改动不能倒推为独立实现读错论文。
- 核心算法闭环已对齐；动力学输出/积分、WM损失、目标预览、Actor信息条件、sampler与Critic语义不同。比较报告是静态机制证据，不把差异当已证明的唯一性能根因，不给虚假的复现完成百分比。
- O1已在 /root/autodl-tmp/robot-repro/supermimic-official-workspace 使用相邻supermimic/mjlab_research及独立Python3.13环境完成训练、两份正式评分和轻量发布。源码、40条格式转换、独立环境均可复用；不重复安装、转换或重启已完成run。原项目.venv、Conda base、G1资产、源码/工作树、数据和其他任务不改。
- 原kevinzakka/mjlab_research地址仍404，但作者README已改为HybridRobotics/mjlab_research且本轮成功取得。后续使用这份作者研究库，不再把旧地址404作为阻塞，也不以普通mjlab或社区实现替代。无需向作者发Issue/邮件来取得本轮已公开的依赖。
- 分开官方当前main基线和论文历史主配置。默认单动作、rep_state/history1不能充当论文完整LAFAN40/proprio/history10；GenCoord/MaxCoord主成绩归属仍待run配置。旧网络权重不能直接作为官方resume。
- 复用已有数据，必要时按真实loader做最小格式适配；130394与129514条成员未对齐，不任意删880条凑数。benchmark.py不是完整评分；完整评测与产物适配不得改核心奖励/失败条件。
- O1保存WM/Actor/Critic、normalizer与config/计数，没有优化器/replay/sampler/RNG完整恢复入口，不承诺full resume。原首段单卡seed0、上限12h、约3h/6h/12h及实际终点评分，已在3h正式R>=.82后正常结束，6h/12h不再执行。训练初始化与必要fill已计入；正式评分与发布已完成。O1不追加训练预算；O2亦已完成，新O3范围按上节和独立协议执行，保留既有LAFAN指标成功与P6—P11成绩。
- BONES后续可用研究库已有packed loader与保留的P9连续qpos/qvel及manifest，沿O1关节/坐标映射生成六字段packed目录；不是重写loader或恢复全部已清理NPZ。130394与129514成员关系未解决，不凑数。当前packed参考全量搬到device，BONES约12.624GiB仅是静态参考容量，不当作总训练显存。
- 既有禁止无关测试/benchmark、轻量Git发布、原件保护与不自动归档/清理约定继续适用。专项H盘迁移另行执行，本轮不处理。

## P12实施（当前暂缓，保留原计划）

- campaign=20261111-p12-world-window-s0；工作树 /root/autodl-tmp/robot-repro/supermimic-p12-world-window。两路full8k_k8_control/full8k_k16_world，tmux sm-p12-k8-control/sm-p12-k16-world。当前只发布分析和计划，不把该状态记成服务器已启动；收到执行启动提示词后直接完成必要实现并正式训练。
- 共同完整resume P11 full8k_residual_control/checkpoint_0036000.pt，恢复三网络、三Adam、sampler G/M、已保存Torch/CUDA RNG、iteration36000、Actor35995、collected646430720及原全局LR。父已知训练431060.78811862133秒单列；P11两路、P10control27000及P9 LAFAN原Critic60000锚点保护且不重评。
- 唯一研究字段world_window=8/16；两路均residual、H32、8192真实/8192想象/WM10×4096、survival_weighted、aux_bce及原奖励/终止/PD/噪声/随机化/LR。source LAFAN2048/BONES6144，reset LAFAN2048/all-BONES5120/hard1024，共享G/M和两个source EMA，不重复更新hard。共享goal710，Actor goal encoder加XYZ后713，另有10×93历史，713不是总Actor输入；.3m反馈尺度和半ActorLR保持。
- loss沿k取平均，每轮仍10次WM optimizer step；候选监督预测步翻倍，不能称等算力对照。Actor参考43帧、collect11帧、history10不改。连续真实日志不跨episode，不padding、不补短窗或改curriculum；k16会改变有效窗口分布。
- 两路各36001–45000，新增9000联合更新或累计本阶段20h先到；每个真实新进程64步fill一次且无WM-only。活跃tmux跨≤4h交互继续，交接不重启replay/LR；真实恢复累计原预算与本阶段统计。全BONES/LAFAN正式节点39000/42000/45000及实际终点，父36k评分复用，不追补训练预算。
- 同输入证据继续configs/p11_fixed_real_windows.json七条P10真实尾窗。父residual36k七窗已发布直接引用，不再推理；仅两P12终点各7×32，共448新增预测步，无新物理/起点扫描。区分仍存活前缀和死后后缀、预测准确度和真实控制收益。
- 复用原forward误差按offset与LAFAN/hard/其余BONES累计z/vz/SO3/state error和样本数，1–8及候选9–16分报。正常已有Replay valid mask只累计proposals/valid_proposals/requested/returned，接受率为valid_proposals/proposals；不新增抽样、前后向、逐步CPU同步或重试框架。原clip/bin曝光、selected≤4/千轮与Critic证据保持。
- 继续两路8k并行，每训练/评分Torch2线程，实际CPU汇总最多12个单线程worker；共用原P9底层只读memmap。P11两训练进程合计83.09GiB显存，不凭旧60GB扩大环境或第三learner。记录原正常节点GPU和cgroup anon/file/inactive_file，不做容量benchmark或重新准备数据。
- GPU评分、指定小证据、Git发布共用原p2-publication.lock、并发1，训练不占锁。P12收尾按实际config的world_window等计算WM预测量，不照抄P11硬编码乘8。复用P11已奏效的进程级http.postBuffer=67108864发布方式，不改全局网络；已有分数推送失败不重训重评。
- 按节点推实际代码/配置、全逐clip评分、紧凑offset/bin统计、指定小证据和真实结论，修正当前handoff状态。推送后不在用户电脑归档；大产物留服务器，原rolling20与里程碑保护照旧，不Release/tar/自动阶段清理。不新增防御性编程及任何单元/mock/冒烟/导入/形状/哈希测试、恢复演练、benchmark或无关扫描。到固定预算如实交付，不自动加预算/新变量/P13。

## P11实施（历史已完成，不重复执行）

- campaign=20261110-p11-root-height-consistency-s0；工作树 /root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency。两路full8k_residual_control/full8k_velocity_height，独立tmux sm-p11-residual/sm-p11-velocity-height。使用现有D57环境、资产和完整库，代码/配置必要实施完成后进入两路正式训练；不重复环境准备。
- 两路共同从P10 full8k_hard_practice/checkpoint_0027000.pt完整恢复三网络、三Adam、sampler G/M、已保存Torch/CUDA RNG、iteration27000、Actor26995、collected461586432与全局LR。父已知沿革382024.04194731265秒单列。保留P10control27k、P9LAFAN原Critic60k锚点，不重评它们；LAFAN已成功不撤销。
- 唯一变量world_root_height_mode：residual对照保留原root-z；velocity_trapezoid候选为z_next=z+.01*(vz_current+predicted_vz_next)，下一vz只取同次WM预测。XY、旋转、关节、速度、70输出与全部Adam状态不变；旧dp_z槽保留但不进入候选z。训练、保存config/checkpoint与同动作证据loader使用同一mode；明确前向语义改变，不称作者公开公式或已证明修复。
- 两路均8192真实/8192想象/WM10×4096，k8/H32、survival_weighted、aux_bce、713/.5、原LR/奖励/终止/PD/噪声与随机化不变；source LAFAN2048/BONES6144，reset LAFAN2048/all-BONES5120/hard1024，hard639仍在all池内，共享G/M且source EMA不重复。继续共用P9底层只读mmap，不重筛/重转/重pack。
- 每路27001–36000、新9000联合更新或本阶段累计20h先到。一次新进程必要64步fill，不新增WM-only；父统计与P11新增量分列，真实恢复累计已耗P11预算。单Codex窗口≤4h，tmux跨窗口连续，交接不重建活跃replay/LR。全库与LAFAN节点30000/33000/36000及实际终点，父27000评分复用；时间截止不同终点以已有共同节点比较，不追补预算。
- 启动前只用原父hard27000对configs/p11_fixed_real_windows.json七条现有真实尾窗各32步同动作预测；终点两WM各同一输入一次，共21rollout/672预测步。不是新物理回放或起点扫描。真实z/vz/SO3/终止误差与正式控制成绩决定结论，候选r_z构造为零不算成功。
- 正常已有collect/k8/H32计算顺带累计三组z-vz残差、真实预测误差，以及hard各50帧bin的collect/WM/Actor起点与flip/handstand原forward物理误差；不新增forward/backward或扫描。设备端累计，按原千轮块/节点转紧凑数据，不加逐步CPU同步。保留原每千轮至多4条selected及actual/raw/weighted Critic证据。
- 两路8k继续并行，Torch各2线程，确有CPU汇总时最多12个单线程worker。P10已实占约89.11GiB，容器RAM上限120GiB含可回收页缓存；不凭旧60GB或宿主available增加环境/第三learner。GPU评分/证据/Git发布共用原p2-publication.lock、并发1，训练不占锁，不停止其他项目。
- 按P10已有长度排序与1024批完整评分，逐clip CSV/1000条，固定hard/general/类别/技能/LAFAN共同质量和保持并列。终点有界失败窗来自同次正式评分。完成时刷新current latest_training/iteration及各完成状态，历史快照另列。
- 推实际代码/配置、完整轻量评分、指定小证据与如实结论后不在用户电脑归档；大产物留服务器，rolling20及里程碑保护照旧。不Release、不tar、不自动阶段清理，不把用户备份作为完成步骤。禁止防御性编程及单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量/吞吐benchmark或无关扫描。真实错误针对修复；不自动扩预算、加其他算法变量或开P12。

## P10实施（已完成，保留执行约定供溯源）

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

P5两支均已完成到24000；本节保留原方案供溯源，当前新增执行入口为顶部O3启动词。

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




