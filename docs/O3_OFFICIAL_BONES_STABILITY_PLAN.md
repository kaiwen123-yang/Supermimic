# O3：官方 BONES 固定学习率稳定性对照

> **历史已完成。** O3训练、全部实际节点评分与轻量发布已完成并于2026-11-13复核。以下保留原执行范围/交接供溯源，不再作为重跑指令；下一阶段使用[O4启动提示词](O4_CODEX_START_PROMPT.md)，结果见[O3复核](O3_REVIEW_20261113.md)。

日期：2026-11-12（北京时间）。本方案基于 [O2完整复核](O2_REVIEW_20261112.md)，固定结果来源 d7acc105accfeca663a2341a846d527dbd10c28b。

**任务：保护O2 3h优秀基线，从同一份3h权重热启动两路官方训练，比较原固定学习率2e−4与四分之一学习率5e−5，研究继续提升困难覆盖时能否保持整体跟踪质量。** 两路唯一训练变量为WM、Actor、Critic共同基础LR倍率。当前交付为方案、协议和启动词；O3运行适配及服务器执行尚未开始。执行端收到[启动提示词](O3_CODEX_START_PROMPT.md)后完成必要适配并正式运行。

## 1. 为什么选择这一段

O2 3h R=.93501955、179失败，6h R=.87472977、397失败，12h R=.62929250、46484失败。3→6h困难覆盖仍提升，但共同完整动作质量下降；12h长动作大幅失稳。已发布训练快照中WM拟合与想象目标改善，没有同样的scalar loss爆炸证据。现有材料没有确认唯一根因。

本段选择固定较小步长，是可直接实施、单一变量的稳定性假设。保留官方Muon/Adam、模型、损失、gamma、采样和训练数据，不同时切换论文历史optimizer/scheduler或修其他差异。5e−5是本项目对照设置，不称作者推荐值或已证明修复。

两支都从相同三网络和normalizer出发，又同样重建未保存的optimizer/replay/sampler/RNG，因此需要原LR控制支。旧O2 6h经过连续训练，不是这次热启动的匹配对照。O2 3h保留为质量锚点，6h保留为困难覆盖参照；不从退化的final继续。

## 2. 身份、版本和固定配置

| 项目 | 安排 |
|---|---|
| campaign | 20261112-o3-official-bones-lr-s0 |
| control run | o3-bones-lr-control-s0 |
| quarter run | o3-bones-lr-quarter-s0 |
| tmux | sm-o3-bones-lr-s0 |
| 服务器 | autodl-d57 |
| 官方工作区 | /root/autodl-tmp/robot-repro/supermimic-official-workspace |
| 复用Python | 工作区/supermimic/.venv/bin/python |
| 官方来源 | SuperMimic abc124c1bd5976341034668af3d12c087f2f1f55 |
| 研究环境 | mjlab_research dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd |
| 隔离O3源码树 | 工作区/supermimic-o3-stability |
| 用户仓库外壳 | scripts/o3，部署到工作区/work/o3 |

| 训练项 | control | quarter |
|---|---:|---:|
| WM、Actor、Critic基础LR | 2e−4 | 5e−5 |
| 三网络LR倍率 | 1 | 0.25 |
| 实际环境 | 4096 | 4096 |
| WM每轮batch | 10×2048 | 10×2048 |
| WM窗口配置 | 8（现代码7个后继转移） | 相同 |
| Actor batch /想象时域 | 4096 / H32 | 相同 |
| 模型与Actor观测 | GenCoord / proprio / history10 | 相同 |
| replay | 每环境1000，ratio16 | 相同 |
| 联合学习触发率 | 0.4/collection | 相同 |
| gamma / lambda | .99 / .95 | 相同 |
| 训练数据 | BONES-only 130394条 | 相同 |
| 初始化seed | 0 | 0 |

奖励、hard终止、PD/action scale、DR/噪声、原return sampler、history padding、网络与loss全部保持父配置。motion slot1、velocity0、wandb_run_path=None。固定hard639仅作分析，不加hard配额或LAFAN训练配额，不引入旧独立实现的XYZ/BCE/存活加权Critic、P11高度/P12窗口等修改。已知GenCoord encoder-bias静态差异留作后续问题，本次不与LR同时修改。

数据直接复用工作区/data/bones130394_official_packed及已有完整身份索引；不再次转换、下载、retarget、删除或重排动作。LAFAN40只作跨库正式评分。

## 3. 两路共同父与准确恢复语义

父权重：

`/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o2-official-bones-s0/checkpoints/checkpoint_000079816.pt`

父历史为79816 collection、326926336真实转移、31924联合更新、约10800.264s训练；BONES R=.9350195502553713，130215条完整。父成绩直接引用，不额外重评。

该checkpoint只有三网络、normalizer/sim-context bundle和配置/计数，没有optimizer、replay、sampler或RNG。因此两路均标为 **weights-only warm-start，full_resume=false**。继承normalizer的count、mean、var、std整体，不只载入权重或单独清零count。新随机流、仿真episode、两类优化器、replay与return sampler均重新建立。

必要加载顺序：

1. 两个child在环境/Runner创建前设置相同torch.manual_seed(0)、env seed0，并采用相同构造顺序。
2. 用既有torch.load接口读取父payload，使用上游load_runner_cfg还原runner_cfg。
3. 在构造Runner/optimizer及第一次CUDA capture前写入各支run_name、cfg.wm.lr与cfg.policy.lr；Critic沿policy.lr。
4. 构造官方环境和Runner；在任何collection或update前执行原接口：

```python
runner._wm.load_bundle(payload["world_model"])
runner.policy_learner.actor.load_state_dict(payload["actor"])
runner.policy_learner.critic.load_state_dict(payload["critic"])
```

5. 使用正常strict加载，在既有对象内复制参数/缓冲，不在optimizer创建后替换网络对象。随后正常env.reset、_seed_sim_history，记录受保护initial节点，进入原训练循环。

相同seed表示匹配初始化；两支策略开始分化后，不承诺相同轨迹或采样序列。两支都按原官方replay.num_transitions≥wm.horizon才学习，Ratio下首次约第9个collection；不加入旧64步fill、先填满1000步、WM-only warmup或恢复演练。

当前Muon LR是Python float，capture后改变属性不会自动改变已捕获运算；Adam LR是device tensor。**本段仅用构造时固定LR，不新增动态scheduler或recapture。** 在initial和正式节点保存实际optimizer类型与LR元信息即可，无需额外试跑。

## 4. 更新数、共享时限与节点

**每路最多新增32000次联合更新；整个campaign只共享一个8h训练墙钟期限。** driver在启动第一条正式训练child前持久化开始时间及deadline=start+28800s。导入、数据加载、初始化、编译、正常replay积累、资源争用、保存、错峰启动及实际中断均在该时限内。准备和训练后评分另计；发布耗时单列统计，但训练期限内发生的发布阻塞或争用仍计入同一deadline，不暂停或扣除。

两支优先并行，每支达到32000新增联合更新或共同deadline即停止。不能为第二支、交接或真实报错重新获得8h。若实际资源条件需要串行，仍遵守同一deadline与更新上限。32k更新约需80k新collection，最终以实际记录为准。

| 节点 | 新增联合更新 | 作用 |
|---|---:|---|
| initial | 0 | 保存已载入父权重及实际初始化元信息；引用父评分 |
| update_08000 | 8000 | 较早变化 |
| update_16000 | 16000 | 中段保持与覆盖 |
| update_32000 | 32000 | 预定主对照终点 |
| actual final | 实际终点 | 预算或真实异常提前结束时如实保存 |

32k若就是final，两个标签引用同一个物理checkpoint，只评分一次。时间上限先到而未产生的节点保持缺失，不补训、不补零值、不造计划节点。新collection、新联合更新、新WM batch/Actor/Critic更新从0分别计数，父历史单列；若展示沿革相加值，注明中间存在权重热启动，不假装optimizer/replay连续。

主对照为双方共同到达的+32k；若未共同到达，使用已保存的最高共同更新节点，并明确原计划未完成。不拿两个不同更新数的final冒充同更新对照。所有8k/16k/32k及实际终点均发布，不只报最优。

父31924加新增32000的沿革更新合计为63924，接近O2 6h的64746，但中间存在权重热启动。这一段主要检验该更新范围内的继续训练稳定性，未覆盖原O2 12h/130314更新尺度，不能据此宣称长期稳定已验证；8h是两路共享的执行时限。

单个Codex交互≤4h，tmux跨窗口继续，交接不重启活动进程。若真实错误导致重启，针对具体错误处理、保留deadline和实际恢复方式；已缺失的优化器状态不称完整恢复，不把失配后的实验静默写成完全匹配。

## 5. 仅补充能区分机制的现有计算统计

开始正式训练前，先从O2现成产物补齐两项只读证据，准备时间单列：在CPU逐份读取3h/6h/final checkpoint中已有normalizer的count与mean/std摘要；从已有console或offline W&B记录提取真实episode reward/length及其训练时间、collection和终止统计（有则提取）。不构造Runner、不恢复试跑、不做新forward或仿真；若原日志没有对应字段，明确缺失并继续本段，不为此安装依赖或补跑。小表回传O2结果目录，用于下次把训练代理量和真实表现对齐。

当前日志缺少真实训练回报与想象目标的分解。两支使用完全相同的轻量统计扩展；不增加Actor/WM/Critic forward，不重新抽replay/reset、不加物理rollout、不更改RNG消耗或学习顺序。

| 统计 | 来源与记录方式 | 回答的问题 |
|---|---|---|
| 真实reward、hard/timeout/motion_end、episode回报/长度 | 直接累计已有collection返回值；GPU计数，正常日志时点转紧凑标量 | 真实训练表现是否已提前回撤 |
| 想象dense return与bootstrap贡献 | 原_train_batch已有reward累积和_bootstrap输出的detach统计 | Policy/reward升高来自哪里 |
| raw/clamped Critic输出、GAE target与上界clamp比例 | 复用同次已算张量，不再调用Critic | 价值目标是否在上界附近集中 |
| normalizer count、mean norm、std min/p50/p95/max | initial和正式节点读取现有buffer | 观测/模型统计是否发生明显变化 |
| hard/普通/category/skill真实reset次数 | 原_external_sampling只调用一次，原样返回其frames，仅计数 | 难度采样是否显著改变实际曝光 |

真实训练episode来自随机起点与DR，不能当正式完整clip R。诊断episode在hard、motion_end或timeout时结束；记录多种done原因是否重叠，不能照抄只在hard终止才清空的最近回报缓冲就宣称完整episode统计。

dense与bootstrap均保留原survival/gamma时序；loss仍使用原表达式。统计只detach reduction，绝不将计数反馈到loss或采样概率。原Critic没有输入normalizer，不捏造该统计；unused velocity normalizer没更新不算故障。原normalizer的int64 count和全部moments整体继承。

reset曝光用原exclusive motion_ends将已有采样frames映射到原source ID。计数从正式initial reset开始，注明边界；不把每步持续存活行算成reset，不加第二次抽样，不每步复制全量索引到CPU。

实现需要的源码统计补丁放在隔离O3官方树，保留固定base commit和完整小diff，两个child用同一补丁。进程级import路径明确指向该树，不能意外使用旧editable安装指向的原树。已有O1/O2源码、环境及Git/stash保持。这里是待实施任务，本计划不声称补丁已完成。

日志按字段明确“窗口累计”或“最后一次update快照”。小统计可按每200行一个JSONL分片发布，避免数千个单行文件；仅推新增/变更分片，完整服务器日志保留。

## 6. 资源与执行顺序

O2普通训练节点整卡读数34253MiB；两同配置进程约67GiB只是容量估计，不是已测的双路峰值。现有卡是RTX PRO6000 Blackwell Server Edition 96GB。按正常启动时已有任务占用安排两路并行；若其他任务使两路无法共驻，使用同协议串行，不停止他人任务，不加容量benchmark或第三learner。

每训练/评分Torch及interop各2线程；纯CPU元数据/汇总最多12个单线程worker。保留packed只读源，主机file cache和anon分别报告，不因大page cache清理用户数据或系统缓存。

pipeline依次执行：

1. 完成必要O3外壳和共同统计补丁，发布实际代码/配置与父来源。
2. 创建一次共享deadline，启动两个正式训练child；各自保存规定节点，训练期间不启动GPU评分。
3. **等待所有训练child真正退出**，释放replay、CUDA图、模型及训练库引用。
4. 一个BONES评分worker加载完整packed库一次，依次评分所有两支/节点的实际唯一checkpoint。每完成一个节点发布其轻量结果。
5. BONES worker退出后，一个LAFAN40 worker评分相同checkpoint。
6. 汇总同更新配对、相对父模型的变化和机制统计，发布结论并结束本段。

正式评分与Git发布继续使用原p2-publication.lock，并发1；训练不持该锁。若一个训练child已结束、另一个仍活动，也暂不启动评分。发布失败只补推已有结果，已完成评分分片保留并从未完成部分接续。

## 7. 评分及结果判读

完整复用O2已修正评分路径：4096固定BONES环境，长度排序32批，末批3418真实+678 inactive；同库多个checkpoint逐一严格加载并冻结normalizer。整段batch reset处于inference_mode，逐批重新铺history10；所有done行含inactive/padding仍做manual reset。LAFAN另建40-env。

frame0、确定性、摩擦1、无训练DR/观测噪声、auto_reset=false，只取消训练timeout，保持官方reward/hard阈值。N−1及失败尾分母、逐clip等权口径不改。不实例化带replay/optimizer的训练Runner来评分。

每节点必须交付全部逐clip CSV（2000行分片）、完整数/失败数/奖励贡献/几何质量；普通category、hard639与补集、四技能、按时长分组。父3h的179失败与3h/6h共同失败57条从已有复核数据读取，仅作固定分析名单。配对报告新增、丢失和共同完整质量，不按clip拼多个模型的最佳表现。

| 结果 | 判读 |
|---|---|
| quarter比同更新control稳定 | 本seed同权重热启动下减小固定步长有收益 |
| 两支均改善 | 热启动后能继续学习；不能独归因于低LR |
| 两支均回撤 | 本次固定低LR不足；利用新真实/价值/采样统计继续定位 |
| 失败更少但R下降 | 覆盖与质量取舍，报告相对父.935的变化 |
| R>.90且失败<179 | 项目库上保持回报参照并改善覆盖；作者25失败仍另列 |
| 缺失共同32k节点 | 报告已完成的共同节点及预算限制，不混不同更新数比较 |

O2 3h质量锚点默认保留。报告完整checkpoint的回报与覆盖取舍后再决定下个父节点，不自动以最后一次或某一项局部最高替换。0.90是SONIC参照，作者25/129514为不同成员集合参考，不虚设.91验收线。LAFAN仍作为跨库结果，不重新定义为O1遗忘，也不新增实机/视频/新seed验收门槛。

每支实际final的同次BONES评分沿O2规则保存最多8条失败小窗：四技能各最低source ID失败1条，其他hard2、非hard2，互斥去重。每窗截至首次硬失败，最多32个真实转移；不足则保存k+1状态、k动作奖励、valid_length=k，不padding、不跨clip/reset、不换候选、不额外重放或WM预测。两支合计最多16窗；缺失败不补。

## 8. 待实施文件与交付

以下是D57执行端的必要适配范围，当前未实现：

| 入口 | 职责 |
|---|---|
| scripts/o3/train_official.py | 共同父加载、构造前LR、共享deadline、新更新计数与保存；学习调用保持官方 |
| scripts/o3/driver.py及run_d57.sh | 两路训练、共同预算和退出后串行两库评分 |
| scripts/o3/evaluate_library.py | 在修正O2基础上支持arm/node、多checkpoint及对父/配对比较 |
| scripts/o3/publish_results.py | 发布实际新代码/配置/分片/统计/结论，保留其他远端改动 |
| scripts/o3/diagnostics.py或小helper及源码patch | 上述同次计算统计、normalizer摘要、已有reset曝光；不新增学习组件 |

Git保存实际代码、小diff、协议和每支actual config、完整逐clip成绩、紧凑诊断/配对统计、指定小窗、结论及当前状态。大checkpoint、数组和完整日志留D57；普通checkpoint每支最近20份滚动，保护initial/8k/16k/32k/final及评分引用权重。只作用于本O3普通节点，O1/O2和历史原件不清理。不Release、不tar、不本机归档或自动阶段删除。

更新README、AGENTS、results/index和campaign summary，准确区分计划、训练中、训练结束待评分、评分中、全部完成。没有完整optimizer/replay/sampler/RNG保存就持续标full_resume=false；不为了本轮增加恢复框架或演练。

必要适配完成后直接进入定义好的正式任务，不加单元/mock/冒烟/导入/形状/哈希测试、容量benchmark或参数搜索。固定预算后交付实际结果，不自动加时、加seed、开O4或恢复P12。


