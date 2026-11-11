# P12 Codex 启动提示词

P11训练、全部正式评分、21条固定WM证据和轻量发布已经完成。本文件发布时P12尚未实施或启动。将下方正文交给连接 `autodl-d57` 的Codex后，直接实施并启动本轮正式研究。

```text
请拉取 https://github.com/kaiwen123-yang/Supermimic 最新main，实施并启动P12，不要只阅读计划或再次给我建议。

先读取AGENTS.md、docs/P11_REVIEW_20261111.md、docs/P12_WORLD_WINDOW_PLAN.md、configs/next_stage_world_window_protocol.json及本文件。P11已完成，不重复启动P10/P11；LAFAN全40 R>=.82已被确认复现成功，不撤销或新增验收门槛。

使用autodl-d57现有主项目 /root/autodl-tmp/robot-repro/supermimic 的activate.sh、.venv、依赖、G1资产和数据；新工作树 /root/autodl-tmp/robot-repro/supermimic-p12-world-window。保留既有工作树、Git/stash、用户改动和其他项目，不setup、安装升级或重建环境。

当前事实：P11高度梯形约束实际正确运行，候选终点多446条完整动作，但全库/困难组回报和固定同输入模型准确度低于原残差；两路flip/handstand均零成功。当前原模型在仍有高存活权重的时段会积累误差并提前预测下坠；不能继续用旧P9“飘高”概括它，也不能称已找到唯一根因。

本轮campaign=20261111-p12-world-window-s0。
两路full8k_k8_control/full8k_k16_world共同完整resume：
/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency/outputs/runs/20261110-p11-root-height-consistency-s0-full8k_residual_control/checkpoint_0036000.pt
恢复三网络、三Adam、sampler G/M、已保存Torch/CUDA RNG、iteration36000、Actor35995、collected646430720与原全局LR。父已知沿革431060.78811862133秒单列。保护P11两路、P10control27000、P9 LAFAN原Critic60000锚点，不重评。

唯一研究变量是world_window：control=8，candidate=16。
两路均world_root_height_mode=residual、H32、8192真实环境/8192想象batch、WM10×4096、survival_weighted Critic、aux_bce、原奖励/终止/PD/噪声/随机化/LR。
source仍LAFAN2048/BONES6144；reset LAFAN2048/all-BONES5120/hard1024，hard639仍在all池内，共享G/M，只按两个source各更新一次EMA。
网络/Adam形状不变；loss仍对k取平均，不翻倍LR。Actor的43帧参考窗、collect11帧、history10不改。WM仍每轮10次更新，但候选监督预测步翻倍，不能称等算力实验。

保持原episode连续采样规则，不跨reset、不padding、不补短窗、不自动改curriculum。k16会减少短episode的有效起点，正常真实/WM/Actor来源与hard-bin计数必须保留。在原forward误差张量上分别统计offset1–8和9–16（候选）的z/vz/SO3/state error及样本数，防止拿16步平均loss直接与8步混比；只复用已有mask累计WM proposals/valid_proposals/requested/returned，按原节点输出，不加额外forward/backward、随机扫描或每步CPU同步。

每路36001–45000，新增9000联合更新，或累计新阶段20h先到。真实新进程仅一次必要64步replay填充，不加WM-only。全BONES与LAFAN共同正式节点39000/42000/45000及实际终点；父36k正式评分复用。沿用1024批、长度排序、完整clip评分和全部逐clip CSV。时间截止不同终点分别报告，以已有共同节点比较，不追补预算。

固定同动作输入继续使用configs/p11_fixed_real_windows.json的7条P10真实尾窗。父residual36000的7条结果已在P11 evidence/full8k_residual_control发布，直接引用，不再启动前推理。只在两个P12实际终点各做7×32，共14条短展开/448新增预测步，复用原action/初态/context/reference，无新物理或起点扫描。看真实预测误差、提前存活衰减及正式控制，不以单个模型统计判成功。

尽快让两路正式训练并行：首路恢复、fill并进入联合循环后立即接第二路，各用独立tmux sm-p12-k8-control/sm-p12-k16-world。每训练/评分Torch2线程，确有CPU汇总时最多12个单线程worker，继续共用P9底层只读memmap。不扩大环境或增加第三learner，不重筛/重转/重pack。用原正常节点记录显存及cgroup anon/file/inactive_file，分清页缓存和120GiB容器上限。

GPU评分、两端小证据、Git发布共用：
/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock
并发1；训练不占锁，不停止其他任务。Codex单次交互<=4h，tmux跨窗口连续；交接不重启训练、不重建活跃replay、不重置LR，也不重新获得20h。

收尾必须按实际world_window/world_batches/world_batch_size计算WM预测量，不能照抄P11硬编码乘8。继续已有发布通路和P11实际解决curl65的进程级http.postBuffer=67108864，不改全局网络、不建自动重试框架；已有评分发布失败就推既有结果，不重训重评。

禁止防御性编程及任何单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量/吞吐benchmark、无关扫描/监控。真正运行错误再针对修复。完成必要实现后直接执行计划内正式训练、评分和证据，不另开测试阶段。

按节点推实际代码、配置、完整轻量评分、正常offset/bin统计、指定小证据和真实结论；刷新当前状态，别留下“已完成但handoff仍叫继续tmux”的误导。
推送GitHub后不在我的电脑归档，不tar、不Release、不自动阶段清理，不把我自行备份列成你完成工作的步骤；大产物留服务器，原rolling20与里程碑保护照旧。到预算结束完成交付，不自动追加训练、换变量或开P13。
```

详见 [执行计划](P12_WORLD_WINDOW_PLAN.md)与[机器协议](../configs/next_stage_world_window_protocol.json)。4小时限制针对一次Codex交互，后台训练按本轮预算连续执行。
