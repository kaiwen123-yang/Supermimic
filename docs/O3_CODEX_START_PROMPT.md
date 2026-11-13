# O3 Codex 启动提示词：官方 BONES 稳定性对照

> **历史已完成。** O3训练、全部实际节点评分与轻量发布已完成并于2026-11-13复核。以下保留原执行范围/交接供溯源，不再作为重跑指令；下一阶段使用[O4启动提示词](O4_CODEX_START_PROMPT.md)，结果见[O3复核](O3_REVIEW_20261113.md)。

本次已完成O2复核并确定O3计划。当前仅发布材料，尚未在D57实施或启动O3。将下列正文交给能够连接autodl-d57的Codex，按固定范围完成必要适配、训练、评分和轻量发布。

```text
请执行 kaiwen123-yang/Supermimic 的O3官方BONES固定学习率稳定性对照。安全同步最新main并保留未提交改动，完整读取AGENTS.md、docs/O2_REVIEW_20261112.md、docs/O3_OFFICIAL_BONES_STABILITY_PLAN.md、configs/o3_official_bones_stability_protocol.json。本轮直接完成必要适配、正式训练、完整评分和Git发布，不停在重新规划，不重复上一轮全仓库审计。

O2已全部完成：3h BONES R=.93501955、130215/130394完整；6h R=.87472977、129997完整；final R=.62929250、83910完整。3h是当前质量锚点，6h是困难覆盖参照。O1/P6已达标成果保留，P12继续暂停。不要从退化的O2 final起步或重跑O1/O2。

使用autodl-d57及/root/autodl-tmp/robot-repro/supermimic-official-workspace，复用supermimic/.venv、固定官方abc124c1bd5976341034668af3d12c087f2f1f55和mjlab_research dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。创建明确的supermimic-o3-stability隔离源码树，只加两支共同的统计扩展；进程级import路径显式选择该树，记录实际来源，不修改原O1/O2工作树、环境、Conda base或其他项目，不安装/升级依赖，不停止他人任务。

campaign=20261112-o3-official-bones-lr-s0，tmux=sm-o3-bones-lr-s0。
两路：o3-bones-lr-control-s0，三网络固定LR=2e-4；
o3-bones-lr-quarter-s0，三网络固定LR=5e-5。
两支均从同一O2 hour_03的
/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o2-official-bones-s0/checkpoints/checkpoint_000079816.pt
加载WM bundle、Actor、Critic及所有已有normalizer。通过原load_runner_cfg恢复配置，构造Runner/optimizer/capture前设置cfg.wm.lr与cfg.policy.lr，任何collection/update前strict加载到既有对象。两支同seed0、同构造/加载顺序，正常reset并铺history。不要只改Adam或capture后的Muon属性。

父只有三网络/normalizer/config，没有optimizer/replay/sampler/RNG；两支同为weights-only warm-start、full_resume=false，未保存状态同样新建，不假装完整续训。normalizer count与moments一起继承。冷replay按官方horizon8就绪条件和Ratio=.4进入原闭环，不加64步fill、1000步prefill或WM-only warmup。

保持官方GenCoord/proprio/history10、单卡每支4096真实环境、WM10×2048/窗口8、Actor4096/H32、replay1000/环境、ratio16、gamma=.99/lambda=.95、原Muon/Adam、reward/终止/DR/采样。唯一训练变量是三网络共同LR倍率1/.25，不同时换scheduler/全Adam、修encoder-bias、加hard或LAFAN配额、改窗口/高度/模型。

直接复用data/bones130394_official_packed及已有身份索引，BONES-only130394条。不要转换/重下载/retarget/筛掉动作，不凑作者129514条。LAFAN仅跨库评分。

正式训练前，CPU只读O2三节点已有checkpoint的normalizer count/mean/std摘要；从现成console/offline W&B提取真实episode reward/length等已有字段，带时间和collection回传小表。不构造Runner、不做试跑或新推理；不存在的字段如实记缺，不安装新工具或补跑。

两路各新增最多32000联合更新，整个campaign共享一个8h训练墙钟。driver在第一条正式child启动前持久化唯一start/deadline；导入、初始化、编译、加载、争用、保存、错峰启动与中断均计入，期间的发布阻塞或争用也不扣除。交接/第二支/报错都不得重置8h。保存新增8k、16k、32k和实际final；32k就是final时只存同一物理节点并评分一次。父31924更新单列，新计数从0。按实际触达节点交付，不补训缺失节点、不把不同更新数的final当匹配对照。本段更新范围接近父后到原O2的6h节点，不能宣称已验证12h/130314更新尺度的长期稳定。

优先两路并行、每进程Torch/interop各2线程，CPU元数据汇总最多12个单线程worker；依据现有任务正常占用安排，不加容量benchmark或第三learner。若已有其他任务使两路无法共驻，用同协议串行并保持共同deadline。单Codex交互<=4h，tmux跨窗口继续，交接不重启活动replay/LR。

两支增加完全相同的必要统计：已有真实collection reward/终止/episode长度；原想象dense return与bootstrap分解；已有Critic/GAE target raw/clamped值和clamp比例；normalizer节点摘要；原_external_sampling实际返回frames的hard/category/skill计数。只detach已有张量并在device累计，按正常日志时点输出；不新增forward/抽样/仿真/逐步CPU同步，不改变loss、梯度、RNG或采样概率。把统计patch和实际source/import路径推到Git。区分窗口累计与最后一次update快照，紧凑统计按JSONL分片发布。

等两条训练child都真正退出后再GPU评分。一个BONES worker只装全库一次，顺序评全部两支/节点的实际唯一checkpoint；退出后一个LAFAN40 worker评同样节点。复用O2修正后的整batch inference_mode、每节点权重/normalizer加载冻结、批量reset/history、inactive/padding manual reset及N−1失败尾分母，逐clip等权。全部实际节点的完整逐clip CSV都要推，未覆盖全库不能报全库成绩；已完成分片和已有评分不因发布失败重算。

比较相同新增更新节点的R、完整/失败、hard/nonhard/技能、时长分组、对父3h的新增/丢失/共同完整质量。读取已发布179条父失败和57条3h/6h共同失败名单作分析，不加训练配额。O2父和6h评分直接引用，不重评；LAFAN称跨库，不称O1遗忘。低LR有效也只限本seed匹配热启动结论，不宣称已定位唯一根因。

每支实际final同次BONES评分可保留原规则最多8条失败尾窗，每窗最多32个真实转移，短窗实际长度、无padding/跨reset/额外重放或WM预测。无需新增视频或实机任务。

沿用p2-publication.lock使评分和Git发布并发1，训练不持锁。推实际代码、配置、共同deadline/计数、全逐clip成绩、紧凑统计、配对结果、小证据和结论，同步README、AGENTS、results/index和campaign summary。大产物留D57；仅新O3普通checkpoint每支滚动20，保护initial/8k/16k/32k/final与评分引用节点。历史产物不清理，不Release/tar/本机归档，不介入H盘迁移。

必要适配完成后直接正式运行，不新增防御性框架、单元/mock/冒烟/导入/形状/哈希测试、恢复演练、benchmark或参数搜索。到固定预算交付全部实际结果，不自动加时/seed/变体、开O4或恢复P12。明确区分方案、已启动、训练结束、评分中、全部完成。
```


