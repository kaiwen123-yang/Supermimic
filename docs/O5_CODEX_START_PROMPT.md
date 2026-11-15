# O5 Codex启动提示词

状态：两路各32000连续更新、全部实际节点评分与轻量发布已完成。以下为原启动提示词；已存在活动O5时只观察接续，不重复启动。实时状态见[执行交接](O5_EXECUTION_HANDOFF.md)。

```text
继续 kaiwen123-yang/Supermimic 的官方代码复现主线。同步最新main，保留现有未提交工作，先读：
1. AGENTS.md
2. docs/O4_REVIEW_20261115.md
3. docs/O5_OFFICIAL_OPTIMIZER_PLAN.md
4. configs/o5_official_optimizer_protocol.json
5. configs/o4_fixed_analysis_groups.json

O4已完整结束，不重启、不追加。它从O3 quarter32k出发、固定5e-5连续132000新更新；BONES父R=.94430475/87失败，O4+16k=.92672114/71失败、+32k=.90437763/93失败，最终=.62798132/47128失败。低LR短期收益成立，但长期退化未解决。O3 quarter16k/32k、O4所有固定节点（含+16k覆盖参照和退化终点）、O2/O1/P6成果保留，P12继续暂停。

本轮直接实施并完成唯一O5任务：
campaign=20261115-o5-official-optimizer-s0
arms=muon_wd0、adam_wd0
runs=o5-bones-muon-wd0-s0、o5-bones-adam-wd0-s0
tmux=sm-o5-optimizer-s0
用户代码工作树=/root/autodl-tmp/robot-repro/supermimic-o5-official-optimizer
官方工作区=/root/autodl-tmp/robot-repro/supermimic-official-workspace

官方源码固定abc124c1bd5976341034668af3d12c087f2f1f55，研究库固定dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。复用官方现有Python3.13 .venv、G1资产、mjlab_research与BONES130394 packed数据。不安装、升级、重建、重下载或retarget，不改Conda base及其他项目。
在官方工作区准备隔离supermimic-o5-optimizer源码树，沿已有supermimic-o3-stability的detached统计补丁并只应用一次，保留原O3/O4源码。增加本轮最小optimizer mode改动，发布scripts/o5/official_optimizer_modes.patch及实际import路径；不将旧独立实现算法混入官方loop。

两支使用完全相同父checkpoint：
/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o3-bones-lr-quarter-s0/checkpoints/checkpoint_000080006.pt
恢复WM bundle含sim context、Actor/Critic与完整normalizer count/mean/var/std；正式采样前strict加载到现有对象，再env.reset与_seed_sim_history。optimizer/replay/sampler/RNG以相同seed0新建，明确weights_only_warm_start、full_resume=false，不能称样本轨迹完全相同。normalizer不清零/冻结。沿官方replay>=horizon起步，不加64步prefill或WM-only。

两支均固定WM/Actor/Critic LR=5e-5，在Runner/optimizer/CUDA graph构造之前设置：
A muon_wd0：保持官方每个Sequential中首尾Linear之间权重交Muon，其余参数交Adam；只将Muon weight_decay显式设0，其余momentum=.95、Nesterov、ns_steps=5、原系数/eps、match_rms_adamw及Adam设置不变。
B adam_wd0：对应各模块所有参数使用torch.optim.Adam，显式weight_decay=0、eps=1e-8、amsgrad=False，保留fused/capturable和device LR tensor；Actor betas=(.9,.95)，WM与Critic betas=(.9,.999)，不换AdamW。
用明确config将模式传至WM/Actor/Critic全部工厂调用；不要导入后只重绑learner_utils.build_optimizers，其他learner已有by-name绑定。不得按保存时临时requires_grad状态漏掉WM参数。

其余全部沿父真实配置：GenCoord/proprio/history10、4096真实环境、WM10×2048/k8、Actor4096/H32、BONES-only130394、replay1000/env、ratio16、gamma.99、lambda.95、官方网络/梯度裁剪/价值上限/奖励/终止/DR/噪声/return sampler。LAFAN仅跨库评分；不改normalizer、encoder bias、根高度、k/H、采样配额，不加cosine，不改从零训练。这是优化器诊断，不能称完整论文Adam+cosine复现。

每支新增32000连续联合更新，两支共64000；保存initial、8000、16000、32000和实际final，final与32k同文件只评一次。预期每支80006 collection、327704576新真实transitions，实际计数为准；继承63924联合更新只记沿革。
wall_deadline_enabled=false、deadline_epoch=null、training_wall_seconds_limit=null。无后台小时截止、不因R或失败数早停、不自动扩预算。交互窗口<=4小时，独立tmux跨窗口连续；交接不重启活跃进程、不清replay、不重置optimizer/LR。实际进程失败如实记录，不自动重启凑连续32000。

从scripts/o4做最小双arm适配到scripts/o5，部署work/o5。不要带回O3旧deadline，也不要遗留O4单路/132k/16-32-64-96-132k硬编码。O4 driver/common.training_state写死low_lr且启动即wait，要改为逐臂状态、两臂启动后统一等待；每臂32000和合计64000分开。版本记录改成实际O5源码，publisher需包含新.patch（旧入口只收.py/.sh）。CODE_ROOT指新用户工作树，PYTHONPATH指新O5官方源码树。保留共同patch使用的self.o3_diagnostics挂载名。父O3评分根、历史O4评分根、历史O2根分开；比较支持每支对父/相邻节点、两支同update、与O4同新增16k/32k历史参照。

优先两支GPU训练并行，各保持4096环境/原batch，独立run/log。若其他实际任务使两支无法同时驻留，让已有一支继续，资源允许后启动第二支，预算不变；不停止其他任务、不缩batch、不做容量或吞吐benchmark。每进程Torch/interop2线程，CPU已有数据分析最多12个单线程worker。若本O5已活动只观察接续，不重复启动。

保留O3/O4 detached诊断。在正常初始化/固定节点记录完整optimizer param_groups：类型、LR、weight_decay、betas或Muon超参数、实际参数名/shape/数量/numel、已安装Torch版本与源码路径；不只记录类型和LR。
同次checkpoint保存补每个参数的detached RMS/Frobenius norm和相对initial比例。从实际factory对象ID映射named_parameters，区分官方Muon inner Linear、其余Linear、bias、LayerNorm；不把任意二维矩阵当Muon、不按requires_grad过滤；初始范数为零时ratio写null。metadata只导出标量超参和名称/shape，不序列化参数张量/optimizer state，不新增forward/backward/RNG采样。
并行做协议列出的六个既有checkpoint（O3共同父+O4五固定节点）的CPU范数读取，用同一分组表，最多一个读取worker，只上传小JSON。不开环境/模型试跑、不额外恢复测试、不扫全盘；缺失节点记录缺失且不阻塞训练。不能把理论衰减乘积当成实测参数缩小，也不能由旧checkpoint倒推出没有保存的optimizer状态。

两个训练子进程确认退出后，一个BONES worker装库一次，串行评分两支所有实际固定节点/唯一异常final，再由一个40-env worker评相同LAFAN节点。一支训练失败仍评分确实保存的可用节点，训练failed/interrupted不改成completed。评分/发布共用原p2-publication.lock，并发1，训练不占锁。
复用整批inference_mode、4096长度排序组批、inactive padding、每clip分母.1*(N-1)、失败尾零与clip等权，原官方终止不改。initial复用父评分，O4+16k/+32k已有结果直接读取；不重评父或历史O4、不新开原配方第三路。

发布全部130394 BONES和40 LAFAN逐clip成绩。主要看固定32k和16k→32k趋势的全库R、相同完整集合R/XY/body orientation、父已成功动作新增失败、新完整/丢失身份及逐动作ΔR，不能只看失败数。给两支/父/O4在16k/32k的共同完整集合质量，并保留全库结果和集合大小。历史O4只是同父同预算参照，不称锁步因果证明；32k不能证明132k长段稳定。
同时报告固定87/179/57/62组、hard639/non-hard、四技能、参考时长和>=60秒494条、LAFAN40/起身。固定组不进训练配额。每支final同次全库评分最多8个32transition失败尾窗，沿既有分组/原ID规则，不额外回放、WM预测或视频。

完成后推实际代码/patch、actual config、全部评分、紧凑训练/范数诊断、小失败窗、比较结论与AGENTS/README/summary/index/handoff。明确训练、评分、轻量发布真实状态；保留历史退出快照且注明语义。历史成果和本轮initial/固定/final/评估引用节点保护，普通新run沿最近20份滚动保留。
大权重/完整日志/数组/轨迹/缓存留服务器，不Release、不tar、不自动归档或阶段清理，未获确认不标已备份。禁止单元/mock/冒烟/导入/形状/哈希测试、恢复演练、无关扫描和benchmark；真实错误定点修复。

直接执行到真实训练、全部实际节点评分和轻量发布完成。交互结束前交接仍在运行的tmux和真实状态，不停止后台。A/B有取舍则如实报告，不拼动作/检查点选最优，不因短段改善宣布长期问题已解决，不自动开O6。
```
