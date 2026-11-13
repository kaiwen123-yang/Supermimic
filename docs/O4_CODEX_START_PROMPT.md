# O4 Codex 启动提示词

> 当前状态：132000连续联合更新已结束，等待评分。以下为原启动提示词；已存在活动O4时只观察接续，不重复启动。实时状态见[执行交接](O4_EXECUTION_HANDOFF.md)。

```text
继续 kaiwen123-yang/Supermimic 的官方复现主线。先同步仓库最新 main 并读取：
1. AGENTS.md
2. docs/O3_REVIEW_20261113.md
3. docs/O4_OFFICIAL_BONES_LONG_RUN_PLAN.md
4. configs/o4_official_bones_long_run_protocol.json
5. configs/o4_fixed_analysis_groups.json

O3已完成，不重复启动。它从同O2 3h父做固定LR对照；quarter+32000为R=.9443047501120772、130307/130394完整、87失败，control为R=.8920829249218997、395失败。quarter16k R=.9475757843950776是质量锚，32k是较佳覆盖锚，两者及O2/O1/P6成果全部保护。P12继续暂停。

本次直接实施并完成唯一O4任务：
campaign=20261113-o4-official-bones-long-s0
run=o4-bones-low-lr-long-s0
tmux=sm-o4-bones-long-s0
D57官方工作区=/root/autodl-tmp/robot-repro/supermimic-official-workspace
O4代码工作树=/root/autodl-tmp/robot-repro/supermimic-o4-official-bones

保留现有工作树及未提交内容，只为O4准备明确代码工作树。复用已有官方独立Python3.13环境、G1资产、mjlab_research和BONES packed数据，不安装/升级/重建/重下载/retarget。核心固定abc124c1bd5976341034668af3d12c087f2f1f55，研究环境固定dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。复用已有supermimic-o3-stability统计源码树并记录实际import路径，不再次apply已存在的diagnostics patch；原官方树及其他项目不改。

父checkpoint：
/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o3-bones-lr-quarter-s0/checkpoints/checkpoint_000080006.pt

明确weights_only_warm_start、full_resume=false。父未保存optimizer/replay/sampler/RNG，不能假称恢复。沿父runner_cfg，在构造Runner/optimizer/CUDA graph之前设置WM、Actor、Critic固定LR=5e-5。严格加载同一WM bundle含sim_context、Actor/Critic及完整normalizer count/mean/var/std到已有对象，正式采样前完成；然后env.reset与_seed_sim_history。归一化不清零/冻结。optimizer/replay/sampler/RNG按O3规则新建，seed0。沿官方replay>=horizon的起步条件，不增加64/1000步prefill或WM-only。

只延长这条已有效的配方：
4096真实环境、WM10×2048/horizon8、Actor4096/H32、GenCoord/proprio/history10；
BONES-only130394，replay1000/env、ratio16、gamma.99、lambda.95；
保持官方Muon/Adam分工、奖励/终止/DR/采样/噪声及其他实际参数。
不加hard或LAFAN配额，不改表示、encoder bias、normalizer、根高度、k/H、Critic权重，不在本段同时切论文Adam+cosine。

本段连续新增132000联合更新。wall_deadline_enabled=false、deadline_epoch=null、training_wall_seconds_limit=null；不设置后台固定完成小时，不因交互窗口到期kill训练。按132000更新或真实失败/用户停止结束；不按R>.90或失败<=25提前停，不自动扩预算。
132000是新优化过程自身长度；祖先63924和终点沿革195924只作溯源，不能冒称O2同初态严格对照或O3 full resume。

在scripts/o4做最小运行适配并部署work/o4。O3 driver/trainer硬编码了共享deadline和32000节点，必须实际移除旧deadline控制分支并换新campaign/parent/run/路径/节点，不能只改文档或重用O3旧budget。保留O3历史代码和结果。无需恢复框架、测试或benchmark，真实运行错误针对修复。

O4 CODE_ROOT指新用户代码工作树，官方PYTHONPATH复用supermimic-o3-stability/src。即时父评分从results/20261112-o3-official-bones-lr-s0/milestones/quarter/update_32000/{source}读取；历史O2根单独保留，不能将原PARENT_CAMPAIGN全局替换后误找hour_03/hour_06。比较改为单路对父和相邻节点。O3非零退出会阻止评分，O4需在子进程确认退出后允许评分已保存节点/确有的异常final，保留训练failed/interrupted及真实更新数，不把评分完成写成132k完成，不自动重启训练。
共同源码patch仍调用self.o3_diagnostics；O4在首次collection前继续挂载CollectionDiagnostics到该属性，不因新阶段命名改成self.o4_diagnostics，也不重复apply patch。

单路训练，保存新增16000/32000/64000/96000/132000及实际final；初始只保存并复用父评分，132k与final同文件只评一次。沿原新run普通checkpoint最近20份滚动保留，initial/固定节点/final/被引用节点保护。记录本段真实collection/联合更新/WM/Actor/Critic计数及耗时。预计330006 collection，实际计数为准。

单个Codex交互窗口<=4小时；独立tmux跨窗口连续。交接不重启活跃进程、不清replay、不重置LR；如本run已活动只接续观察。进程真实退出后，记录真实连续段及错误，不自动重启凑连续132k，也不重头重跑。训练/评分Torch和interop各2线程；CPU已有数据分析最多12个单线程worker可并行。共享现有GPU，不停其他任务，不另开高LR对照或参数搜索。

训练子进程实际退出后，一个BONES worker装库一次顺序评所有实际固定节点/唯一异常final；之后一个40-env worker评相同LAFAN节点。评分与Git发布共用原p2-publication.lock，并发1。沿O3全程inference_mode修正、4096长度排序批和inactive padding，N-1完整时长分母/失败尾零/clip等权/官方终止不改。父节点不重评。

发布每节点全部130394与LAFAN40逐clip评分。分析父87失败、O2原179及共同57、O3 16k→32k丢失62等configs固定集合，统计新学会/丢失/共同完整质量、hard639/non-hard、四技能、长动作494条及LAFAN跨库表现。固定集合不影响训练采样，不挑动作跨checkpoint拼接。尤其并报handstand完整数和身体姿态质量。

复用O3已有detached诊断：真实collection reward/所有done episode统计、dense/bootstrap、raw/clamped value及GAE目标、normalizer、实际reset曝光；保留窗口总量与最后更新快照的区别，不添加forward/physics/RNG抽样。实际final同次全库评分取<=8失败尾窗、每窗<=32真实transitions，沿O3固定组和source ID规则；不额外回放、WM预测或视频。

完成后推实际适配代码、config、全部逐clip、紧凑诊断、小失败窗、比较结论及AGENTS/README/summary/index。当前训练/评分/轻量发布状态保持一致；历史training_completed_evaluation_pending快照可保留并标明历史。大权重/日志/数组/缓存留服务器，不Release、不tar、不在用户电脑归档、不自动清理；保留历史成果，未确认不标已备份。禁止单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量/吞吐benchmark和无关扫描。

直接执行到真实训练、正式评分、轻量发布完成；交互结束前交接仍在运行的tmux和实际状态，不停止后台。发布后交付本段所有节点和后续判断，不自动开O5。
```

