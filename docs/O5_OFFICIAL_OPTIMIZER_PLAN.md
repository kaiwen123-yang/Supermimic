# O5：官方优化器配方的同父短段对照

日期：2026-11-15。依据：O4 完成结果 `b3a3eac724fa4bc4dd8781dc7c8fb371e95efef8`，以及[O4完整复核](O4_REVIEW_20261115.md)。运行适配已部署；当前状态 **训练已退出，正在全BONES评分**，见[执行交接](O5_EXECUTION_HANDOFF.md)与campaign summary。以下保留完整执行方案。机器可读约定见[协议](../configs/o5_official_optimizer_protocol.json)，执行入口见[Codex启动词](O5_CODEX_START_PROMPT.md)。

## 1. 本轮要回答的问题

O4 已完整完成新增132000次连续联合更新，低LR并未避免长段退化。父O3 quarter32k的BONES R=.94430475、87失败，O4+16k变为.92672114、71失败，+32k变为.90437763、93失败；因此在大规模失败出现前，已有可观察的质量下降。最终R=.62798132、47128失败，不能继续从这个最终节点追加训练。

本轮将预算集中到一个已经找到明确源码依据的问题：**当前官方隐藏矩阵的Muon更新及其默认权重衰减，是否参与了这段早期质量退化？** 两条新分支都从与O4相同的O3 quarter32k父节点开始，每条只做32000新联合更新。O4已发布的16k/32k作为历史参照，不重新跑第三条原配方。

| 版本 | 隐藏Linear权重 | 其余参数 | 三网络LR | 新更新 |
|---|---|---|---:|---:|
| O4历史参照 | 官方Muon，默认weight_decay=.1 | 官方Adam，默认weight_decay=0 | 固定5e-5 | 复用16k/32k |
| A `muon_wd0` | 同一Muon分组，仅显式weight_decay=0 | 同原Adam | 固定5e-5 | 32000 |
| B `adam_wd0` | Adam，显式weight_decay=0 | Adam，显式weight_decay=0 | 固定5e-5 | 32000 |

A与历史O4相比只去掉Muon衰减；B与A相比，在两者均无衰减时改变隐藏矩阵的优化更新方式。两个分支固定8k/16k/32k节点，不挑最好的节点后自动延长，也不在本轮添加第三路或参数扫描。

## 2. 为什么选择这个对照

官方当前工厂把每个`nn.Sequential`中首尾Linear之间的Linear权重交给Muon，其余参数交给Adam。引入Muon的[官方提交](https://github.com/HybridRobotics/supermimic/commit/0e5ff6bb00166fdbdb308ce23583f55948504fac)明确采用默认decoupled weight decay=.1。这是作者当前实现中的选择，不能称为已经证实的代码错误。此前O3改变LR也同时改变了`lr * weight_decay`的衰减力度，因而O3的短期改善不能仅解释为梯度步幅变小。

[PyTorch v2.14.0实现](https://github.com/pytorch/pytorch/blob/v2.14.0/torch/optim/_muon.py)使用基础LR做`param *= (1 - lr * weight_decay)`，`match_rms_adamw`的形状倍率只作用于后续更新项。每次联合更新，Actor/WM/Critic分别有1/10/20次optimizer step。这使该项在长训练里值得单独研究，但现有O4没有记录实际权重范数，不能从理论乘积推断参数已经缩小到某个比例或认定唯一根因。

[论文v2 Table A.5](https://arxiv.org/pdf/2610.28480v2)指定Adam、单卡基础LR2e-4、250000 iterations余弦衰减至.03倍，再保持到320000 iterations。表中没有单独注明weight_decay=0；这里的零值对应官方原Adam实现及PyTorch默认行为。**O5是优化器诊断，不是完整论文配方的最终复现。** 当前尚未确认论文历史调度器的iteration与现在collection/joint counter的精确对应。把Adam、2e-4、cosine、从零训练同时改动会使本轮原因难以判断。本轮先固定LR和起点，后续再根据结果决定值得投入的连续长程方案。

## 3. 环境、起点与真正的变量边界

campaign：`20261115-o5-official-optimizer-s0`；两run：`o5-bones-muon-wd0-s0`、`o5-bones-adam-wd0-s0`。使用独立`sm-o5-optimizer-s0` tmux承载driver及两个训练子进程，各run/log/结果目录隔离。

用户代码工作树：`/root/autodl-tmp/robot-repro/supermimic-o5-official-optimizer`。官方工作区仍为`/root/autodl-tmp/robot-repro/supermimic-official-workspace`；新增隔离官方源码树`supermimic-o5-optimizer`。它以官方`abc124c1bd5976341034668af3d12c087f2f1f55`为基础，包含既有O3 detached统计补丁和本轮最小优化器模式补丁。原`supermimic-o3-stability`以及O3/O4工作树保留，已有统计补丁只应用一次。研究环境固定`dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd`，复用现有官方Python3.13 `.venv`、资产和数据；不安装、升级、重建或重新retarget。

两分支的共同父checkpoint：

```text
/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o3-bones-lr-quarter-s0/checkpoints/checkpoint_000080006.pt
```

加载完整WM bundle（含sim context）、Actor、Critic及全部active normalizer的count/mean/var/std；在正式采样前加载到已构造对象，再执行env.reset与`_seed_sim_history`。optimizer、replay、return sampler与RNG按相同seed0重新初始化。明确`weights_only_warm_start`、`full_resume=false`，不宣称两个分支或历史O4具有逐样本相同轨迹。normalizer继续原更新规则，不冻结、不清零。

共同保持：BONES-only130394；GenCoord/proprio/history10；4096真实环境；WM10×2048、k8；Actor4096、H32；replay1000/env、ratio16（约.4 joint/collection）；gamma=.99、lambda=.95；原网络、梯度裁剪、价值上限、reward、终止、action/sensor noise、DR与return sampler。LAFAN40仅作跨库评分。沿官方replay>=horizon起步，不增加64步prefill或WM-only。

Adam准确参数为：Actor betas=(.9,.95)，WM/Critic betas=(.9,.999)；全都`weight_decay=0`、`eps=1e-8`、`amsgrad=False`，保留fused/capturable和同地址device LR tensor。B使用`torch.optim.Adam`，不换成AdamW。A的Muon保留momentum=.95、Nesterov、5次Newton–Schulz、原系数和eps、`match_rms_adamw`；仅将其decay设为0。

## 4. 最小运行适配

从已执行的O4 adapter复制到`scripts/o5`，部署到官方工作区`work/o5`。调整为两arm和8k/16k/32k节点；不能带回O3的共享8小时deadline，也不能留O4单路与132k硬编码。新配置显式传递优化器模式到WM、Actor、Critic的所有工厂调用，在构造optimizer与CUDA graph之前生效。

不要在模块导入后只重绑`learner_utils.build_optimizers`：`wm_learner`和`policy_learner`已经按名字绑定该函数，可能仍调用旧对象。采用隔离源码中的明确工厂/config改动，并发布实际patch与import路径。Muon分组仍严格沿官方inner Linear规则，不用“所有二维参数”替代。新Adam必须包含对应模块的全部参数；不能依据保存时临时的`requires_grad`状态漏掉WM参数。

`CODE_ROOT`指向本轮用户代码工作树，`PYTHONPATH`指向新O5官方源码树。共同统计patch仍调用`self.o3_diagnostics`，首次collection前保留此挂载名称。O3父评分、O4历史16k/32k、O2历史证据三个根路径分开，避免全局替换campaign后找错`hour_03`等旧节点。

O4 driver写死`low_lr`并在启动后立即wait，`common.training_state`也写死该key；O5必须改为逐臂状态、先启动两臂再统一等待，不能只改ARMS。发布计数区分每臂32000与合计64000。原版本记录枚举的`supermimic-o3-stability`换成实际O5源码；原publisher只收`.py/.sh`，须显式发布新增`.patch`。

driver等待两个真实训练子进程退出再评分。一支实际失败不停止另一支；之后评分确实存在的已保存节点和可用异常final，同时保留failed/interrupted状态及真实update数。不因评分结束改写成32000完成，不自动重启或拼接连续段。

## 5. 有限预算与并发

每支新增32000 joint updates，共64000；各保存initial、8k、16k、32k及实际final，32k/final同文件去重。预期每支80006 collection、327704576新真实transitions、320000 WM minibatch、32000 Actor、640000 Critic minibatch更新；实际计数为准。继承normalizer count654630912，完整预算后预期982335488。祖先63924与终点沿革95924仅用于溯源。

`wall_deadline_enabled=false`、`deadline_epoch=null`、`training_wall_seconds_limit=null`。按有限更新预算、真实执行失败或用户明确停止结束，不按R或失败数早停。单Codex交互<=4小时，后台tmux跨窗口连续；交接不重启、清replay或重置optimizer/LR。

优先在现有96GB GPU上两支并行，每支保留4096环境及原batch。若其他实际任务使两支不能同时驻留，保持已经运行的一支，在资源允许时接第二支，预算仍各32000；不停止其他任务，不缩batch，不做容量/吞吐benchmark。各Torch/interop2线程，CPU元数据分析最多12个单线程worker；历史checkpoint读取最多一个CPU worker，不为占满资源新增任务。

正式GPU评分与Git发布共用原`/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`，并发1，训练不占锁。分别记录每支训练耗时、campaign墙钟、正式评估与发布耗时，不把不同共享条件下的速度差当优化器效果。

## 6. 评分和结论应如何比较

所有训练子进程退出后，一个BONES worker装库一次，顺序评两支的全部实际固定节点/唯一异常final；退出后一个40-env LAFAN worker评相同节点。复用O3/O4已修正的整批`inference_mode`、4096长度排序组批、inactive padding与原终止。每clip R=完整实际native reward sum/[.1×(N−1)]，失败尾部补零后clip等权平均。父初始和历史O4评分直接读取，不重新仿真。

必须同时给出：

- 全库R、完整/失败数、完成比例、全部逐clip、逐动作ΔR分布；保留失败结果。
- 每支对父、相邻节点、两支同update，以及16k/32k对历史O4的新增完整/丢失/共同完整集合。
- 同一完整集合的R、XY、身体姿态；另在父+O4+A+B共同完整集合比较16k/32k，注明集合大小，避免各组条件均值用不同动作。所有条件结果旁保留全库成绩，不能靠排除失败制造优势。
- 原固定87/179/57/62分析组、hard639/non-hard、flip44/side_roll22/cartwheel120/handstand160、参考时长组与>=60秒494条。固定组只用于分析，不进入训练配额。
- LAFAN40跨库成绩和六条起身。不能将BONES-only新checkpoint的LAFAN差解释为既有O1被覆盖。

判断以32k固定终点和16k→32k趋势为主，8k仅补过程。R、同动作精度和父成功保持一致改善时才称该段有综合收益；出现取舍则并列报告，不用失败数单独宣布胜者。此处是研究判断，不新增LAFAN验收门槛，也不机械要求在不同成员的130394库上达到作者129514库的25失败。

## 7. 诊断只补本轮缺的证据

复用既有detached日志：真实reward与reset窗口总量、所有done/episode统计、dense/bootstrap、raw/clamped value与GAE、Actor裁剪前梯度、normalizer与实际reset曝光。loss/imagination是每个日志窗口最后一次joint的快照，不能当成所有更新的均值。

在正常初始化和各唯一固定/实际final保存点，记录实际optimizer类、所有group超参数、参数名/shape/数量/numel、LR、decay、betas或Muon设置。用正常启动读到的已安装PyTorch版本/源码路径和实际构造结果确认默认值，不追加导入测试或玩具更新。

在同一保存流程增加detached参数RMS/Frobenius norm与相对initial比例。用真实factory参数对象ID映射`named_parameters()`，区分官方Muon inner Linear、其他Linear、bias、LayerNorm affine。不得把normalizer缓冲误当可学习权重，不按瞬时`requires_grad`筛选。初始范数为零的ratio写null并保留绝对范数；optimizer元数据只导出标量超参与名称/shape，不序列化参数张量或optimizer state。只保存小摘要，不复制大矩阵进Git，不做新forward/backward/RNG采样。

同时允许一项有限CPU只读分析：协议中已列出准确路径的**O3共同父+O4五个固定节点，共六个独立checkpoint**，提取同分组范数，输出`historical_o4_weight_norms.json`。分组映射复用O5正常构造获得的信息；不额外构造测试模型、不恢复optimizer、不开环境、不做rollout或恢复演练。缺失节点记录缺失，不全盘找文件、不恢复下载、不阻塞训练。旧checkpoint没有optimizer状态，范数分析不能倒推出实际decay超参数。

每支实际final在同次完整BONES评分里取最多8个失败尾窗、每窗最多32真实transitions，沿既有技能/其他hard/non-hard与最小原ID规则。没有失败的组不补造样本；不增加物理回放、WM预测或视频。

## 8. 本轮结束后的决策边界

| 观察 | 可作的判断 |
|---|---|
| A、B都比历史O4同预算有一致质量收益 | 去衰减是值得继续研究的共同变化；结合范数证据，不直接认定唯一根因。后续可优先选择更贴近论文且质量更好的Adam配方。 |
| 只有B改善 | 去衰减本身不充分，Adam更新方式可能带来额外收益。下一份计划集中到Adam的连续长程和明确cosine时钟。 |
| 只有A改善 | 当前热启动下Muon无衰减更适合；不能因此否定论文Adam从零配方，5e-5也不是论文基础LR。 |
| 两支都退化 | 停止自动扩展；这一组优化器修改不足以解释/解决问题，下一次根据模型与数据证据决定机制或从零论文配方，不继续机械降低LR。 |

历史O4不是本轮同步重跑的随机对照。seed0不能消除GPU与自适应轨迹差异，逐clip数量大也不能替代独立seed。32k最多说明已有早期质量问题是否缓解，不证明132k或论文终点稳定；不因此追加多seed等用户未要求的验收条件。未来cosine若实施，必须明确collection/joint计数并用同地址device LR tensor更新；当前Muon float被capture固定，不能只套Python scheduler。

## 9. 发布与保护

先推实际adapter/patch、actual config、完整评分、紧凑训练诊断/参数范数、有限失败窗与真实结论，同步AGENTS/README/summary/index和handoff。原initial/固定节点/final/被评估引用的checkpoint保护；普通新run只沿最近20份滚动规则。O3 quarter16k/32k、O4+16k覆盖参照、O4退化节点、O2/O1/P6与其他历史保护成果全部保留，P12继续暂停。

大权重、完整日志/轨迹/数组和缓存留D57；不Release、不tar、不自动归档或阶段清理，未获用户确认不标已备份。禁止单元/mock/冒烟/导入/形状/哈希测试、恢复演练、无关扫描/报告和额外benchmark。遇到真实错误再定点修复。完成本轮真实训练、所有实际节点评分和轻量发布后交付，不自动开O6。
