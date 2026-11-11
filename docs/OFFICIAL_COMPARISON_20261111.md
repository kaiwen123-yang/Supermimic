# SuperMimic：独立实现、论文与官方源码对照（2026-11-11）

## 结论与本次范围

**独立实现已经抓住论文的核心学习闭环，LAFAN1 对应效果指标已经达到；但现有训练系统与官方当前源码在动力学参数化、误差度量、参考时间窗、策略信息条件、采样和数值优化上存在多组实质差异。下一步优先建立独立的官方运行基线。**

本次读取代码、配置、已发布结果和论文，没有运行新的训练、模型推理或全量评分，也没有修改服务器环境、停止现有任务或迁移数据。检查覆盖两仓库核心算法/训练/任务/评测代码、当前与历史关键配置，以及 P6—P11 的结果汇总和相关诊断；没有把尚未逐行复算的所有逐动作 CSV 声称为已重新验证。

| 对照对象 | 固定来源 |
|---|---|
| 用户独立实现 | kaiwen123-yang/Supermimic，dd28b969e7ab33a3e285f2caa7469e745f7cb5a0 |
| 官方公开源码 | HybridRobotics/supermimic，5efbf114e11f725c31d83e217be987c13c0e4ce2 |
| 论文基准 | 仓库长期依据 arXiv:2610.28480v1；本次同时复核现行 PDF v2 的核心方法与附录参数 |
| 当前实验状态 | P11 已完成；被审查提交中的 P12 仍为计划，未实施/启动 |

“官方当前 main”“产生论文主表成绩的原始代码与运行配置”“本项目独立实现”必须分别记录。不能把当前 main 的每个差异都倒推为我们读错了论文。

## 1. 当前到底复现到什么程度

以下数值来自各阶段 summary.json 的实际结果字段；原有 LAFAN1 指标验收结论保留。

| 模型 | 数据 | 完整时长归一化回报 | 完整动作 |
|---|---|---:|---:|
| P6 feedback33000 | LAFAN1 | 0.86624655 | 37/40 |
| P9 原 Critic60000 | LAFAN1 | 0.89043870 | 38/40 |
| P7 从零9000 | LAFAN1 | 0.52562120 | 20/40 |
| P10 control27000 | 本项目全 BONES | 0.86659060 | 129579/130394 |
| P11 residual36000 | 本项目全 BONES | 0.86375135 | 129152/130394 |
| P11 velocity-height36000 | 本项目全 BONES | 0.85693786 | 129598/130394 |

来源：[P6结果][U-P6]、[P7结果][U-P7]、[P9结果][U-P9]、[P10结果][U-P10]、[P11结果][U-P11]。

用户已确认“达到作者对应实验指标即可认定该项成功”。P6 超过 LAFAN1 的 0.82 参照，因此该项效果复现已经成功。不能事后追加 40/40、从零耗时、多种子或实机条件来撤销这个成果。新的官方对照会明确观测信息、训练来源和配置差异，范围与原验收记录分开。

### P11 的剩余问题集中在哪里

| 指标 | 原残差 residual36000 | 高度一致性候选 velocity-height36000 |
|---|---:|---:|
| 全 BONES 失败动作 | 1242 | 796 |
| 固定 hard639 完整 | 312/639 | 305/639 |
| hard639 回报 | 0.44230236 | 0.43351596 |
| flip | 0/44 | 0/44 |
| side_roll | 20/22 | 20/22 |
| cartwheel | 90/120 | 81/120 |
| handstand | 0/160 | 0/160 |
| 同一模型的 LAFAN1 保持回报 | 0.73313568 | 0.71080315 |
| LAFAN1 完整 | 29/40 | 29/40 |

候选多完成446条动作，但总体回报更低，困难动作完成数也未改善。这里同时存在动作完成、执行质量、困难技能和跨数据保持四个问题；不能仅以完整数判断优劣。[P11结果][U-P11]

论文主基准为129514条，本项目为130394条，时长分别约264.56h与264.430633h。数量差880并不能说明本项目仅多了880条，具体交集和差集尚未由作者清单核实。论文单H100约3h时失败25条、双H100约9.8h时失败0条，可作为目标参照，不能直接将1242/25当同一数据集的严格性能倍数。论文的0.90是 SONIC 参照线，不是 SuperMimic 精确最终回报。[论文][PAPER]

P7 从零9000用了约9.9907h仍为0.52562；P11 residual新增阶段约13.6213h，包含父模型的已知训练沿革约119.7391h。后者含LAFAN预训练、迁移和续训，且是共享GPU进程墙钟，不是独占GPU-hours。历史最高分不能当作一次从零训练的1.2h或3h成绩，也不能直接与H100计算严格速度倍数。[P7结果][U-P7]、[P11结果][U-P11]

## 2. 核心思路有哪些已经做对

代码核对支持以下一致点：

- 真实仿真采样、写入 replay、多步自回归拟合世界模型、再更新策略与 Critic 的交替闭环。
- 策略更新时冻结世界模型参数，同时保留状态和动作经过世界模型的梯度。
- H32 想象展开、末端 Critic bootstrap、gamma=0.99、lambda=0.95。
- 世界模型、运动编码器/解码器、Critic 的主要隐藏层宽度与论文表中对应。
- Actor 的 Adam beta2=0.95、全局梯度裁剪1.0后逐元素裁剪0.1，以及Critic每轮5×4更新。
- 跟踪奖励主体的六个正奖励项、相对身体位姿对齐、动作平滑与关节限位惩罚高度一致。
- 现有正式评测使用整条动作、从首帧开始、确定性策略、摩擦1、无观测噪声/随机化，并计入失败后未执行尾段；覆盖率另作诊断。

这说明问题不在于完全走成了另一种算法，也不是神经网络宽度普遍不够。关键是论文没有展开到源码级的实现选择，以及后续为了稳定运行添加的项目方法。[用户学习器][U-learning]、[用户奖励][U-task]、[官方策略学习器][O-policy]、[官方奖励][O-reward]、[用户评测][U-eval]

## 3. 主要差异：按影响机制排序

### 3.1 世界模型输出结构不同：自由位姿残差与一致积分

用户模型输出70维，分成35维位姿/关节残差和35维速度残差。位置更新包含“旧位置 + dt×旧速度 + 独立位置残差”，速度由另一组残差更新；姿态和关节也存在类似的独立自由度。[用户模型74—98行][U-model]

官方 GenCoord 只输出35维速度增量，包括根线速度、根角速度、29个关节速度增量。根XYZ、根姿态和所有关节位置都由这组增量解析积分，再从积分后的根姿态导出重力方向。它的模型输入采用完整body frame的68维状态，而本项目采用heading/yaw处理后的100维特征。[官方状态表示469—554行][O-rep]、[官方坐标变换][O-gen]

这与P10/P11发现的位姿—速度不一致直接相关：官方结构减少了网络分别“编造位姿和速度”的自由度。不过，静态差异尚不能证明它解释了全部失败。

**P11 的局部尝试并不等价于官方结构。**P11只把根高度z改成梯形积分，其他位姿/关节仍保留自由残差。官方对全部自由度一致积分，且子步系数 c=(d+1)/(2d)，d=4时为0.625；P11局部梯形系数为0.5。候选未获胜不能作为官方整体方案无效的证据。

官方还提供 MaxCoord 的逐刚体表示、积分和解析IK路径，本项目没有对应实现。论文没有直接指明主成绩究竟对应当前哪一分支；需要论文运行配置定位，不能凭名称选一个后声称匹配论文。

### 3.2 世界模型损失的量纲与权重差异很大

双方都出现70通道均值，但这70个通道不是同一组量：

| 监督内容 | 用户独立实现 | 官方当前 GenCoord |
|---|---|---|
| 根位置 | 原始米误差平方，权重1 | 名义误差0.01m，权重10000 |
| 根姿态 | 3维旋转向量平方，权重1 | 缩放后的9维旋转矩阵差，名义误差0.02，权重2500 |
| 关节位置 | 权重1 | 名义误差0.1，权重100 |
| 关节速度 | 先除10，平方后权重0.01 | 名义误差3.14，权重约0.1014 |
| 根线/角速度 | 直接参与监督，手工缩放 | 不作为独立loss通道，经过积分位姿监督 |
| 终止网络 | 额外学习终止头，主线保留BCE | 当前WM仅状态监督，没有学习型终止头/BCE |

官方采用按名义允许误差归一化的 Bryson 权重。旋转度量不同，不能把2500写成全角域精确损失倍数；根位置/关节位置的权重差异则直接可见。[用户误差定义129—139行][U-model]、[用户WM更新][U-learning]、[官方WM损失][O-wm]、[官方根姿态loss][O-rep]

**本项目WM MSE很小，不代表已达到论文0.007—0.011的同一误差标准。**不同监督量、不同尺度、不同采样分布下，标量MSE不能直接横向比较。

论文允许解析或学习型头，并注明解析头没有相应学习损失。我们此前的BCE是独立实现的选择，P3对照支持在当时那套实现中保留它。官方当前不使用BCE，不能反推在旧模型上单独删BCE一定改善。

### 3.3 同样是“10帧目标”，预览时长差了很多

| 项目 | 用户实现 | 官方当前实现 |
|---|---|---|
| 目标帧索引 | t+1…t+10，连续未来帧 | t、t+5…t+45 |
| 50Hz下覆盖时间 | 0.02—0.20s | 0—0.90s |
| Actor目标内容 | 每帧q、dq、高度、相对姿态、根线/角速度，共710维；P6后另加当前XYZ误差3维 | 每帧q、dq、相对姿态，共640维；Actor显式不接收根相对平移 |
| 当前传感器观测 | 10×93历史 | 默认rep_state/history1；可选择proprio/history10 |

对翻腾、起跳、倒立等需要提前准备的动作，0.2秒与0.9秒的参考预告可能明显改变可学习控制。这个推断有直接机制依据，但尚无同条件消融量化收益。[用户目标窗口90—130行][U-motion]、[官方目标窗口95—234行][O-rep]

P6加入XYZ后大幅改善了旧模型的位置漂移，这项实验结果仍然有效。官方将平移信息留给Critic/世界模型目标而不传Actor，是另一套信息条件。新官方基线应先遵循自己的接口，不能把713维旧Actor输入直接移植后称原版。

默认官方rep_state还包含根高度/线速度等状态信息，且不走proprio噪声路径。论文部署策略使用10帧本体观测历史。因此默认官方单动作成绩不能直接用来判断论文传感器条件的效果。[官方runner][O-runner]

### 3.4 相同50/40/10采样比例，实际分布并不一样

| 机制 | 用户ReturnSampler | 官方ReturnSampler |
|---|---|---|
| 初始bin回报 | 0 | 最大可能回报 |
| 更新时刻 | episode结束 | 每20步 |
| 跌倒/自然末尾/timeout | 统一boundary，有限回报，尾值0 | 跌倒尾值0；自然末尾用均值V；timeout/窗口末尾用下一bin的V |
| 回报统计 | 固定0.9/0.1 EMA | 按访问计数平均，历史计数上限256 |
| 10%历史保持 | softmax权重的EMA | 全运行累计focus平方 |
| 当前项目额外分层 | 25% LAFAN、75% BONES，并含hard重置配额 | 依实际官方配置，不能默认带入项目配额 |

一个可由公式直接推出的风险：即使每步奖励都是理想的0.1，用户自然尾部只剩1步/8步时，有限折扣回报也仅0.1/约0.7726，远小于最大无限回报10。负回报softmax可能把这些自然尾段当成困难区。官方bootstrap处理减轻了这种长度偏置。这是需重现的实质机制，不是已证明的flip失败单一根因。[用户sampler9—96行][U-env]、[官方sampler][O-sampler]

现有P11证据显示，4220个合法k8困难bin都有WM曝光；66个零起点bin是参考末尾不足8步。不能再用“关键开头完全没进learner”概括当前问题。[P11复核][U-review11]

### 3.5 Critic、软终止和参考末尾语义不同

- 用户P11使用按存活权重归一化的Critic MSE，没有value/target上界。官方当前使用普通MSE，同时把bootstrap和GAE target限制在最大可能回报以下；只有上界，不能写成夹到[0,10]。
- 用户软终止是两个sigmoid概率的OR；官方是先取归一化误差最大值，再计算一个sigmoid。相同温度0.05不保证相同概率或梯度。
- 用户想象到自然clip末尾设p=1；官方保持最后参考帧，软终止由几何误差决定。
- 官方真实硬终止阈值取自尚不可访问的研究版环境，当前主仓库不足以核实全部继承值。
- 用户WM的world_window=8监督8个转移；官方当前wm.horizon=8采8帧，实际监督7个预测转移。参数名相同不意味着窗口语义相同，暂不把这一点命名为已证实bug。

这些机制都改变学习目标或采样分布，不能只复制某个clamp或概率公式到旧系统后期待恢复作者表现。[用户学习器][U-learning]、[用户模型][U-model]、[官方策略][O-policy]、[官方想象环境][O-wmenv]、[官方WM学习器][O-wm]

### 3.6 数值实现与训练执行差异

用户采用Linear+ELU、固定尺度、普通Adam、余弦LR，当前Actor再乘0.5；官方当前采用Linear+LayerNorm+GELU、经验归一化，中间Linear权重Muon而其他参数fused/capturable Adam，当前主循环未发现论文所述余弦调度。

官方正常采样更新normalizer，真实和想象前向复用同一统计；WM和策略更新使用torch.compile及CUDA graph。本项目存在更多Python循环、标量读回、同步和每轮完整checkpoint写入。每轮保存是既有用户要求，不能擅自取消，但应在解释效率差距时与模型优化成本分开。[用户模型][U-model]、[官方模型][O-model]、[官方优化][O-opt]

不要误报的相同点：网络隐藏层宽度基本一致；Actor beta2和两级梯度裁剪本来就一致。官方replay_ratio=16经过4096/(10×2048×8)×16换算，训练触发比例为0.4；不能将16当作和论文0.4不同的UTD。官方max_iterations统计collection轮，本项目统计联合更新轮，二者不能直接相除。

## 4. 为什么当前官方main也不能直接当论文原配方

有明确的源码历史证据：

- [0e5ff6b提交][O-muon-commit]加入Muon；提交说明的对比使用LAFAN40、MaxCoord和god-mode配置。
- [aec4a5e提交][O-ln-commit]统一LayerNorm/GELU，并明确更改后旧actor/world-model文件不兼容。
- 论文原始v1及当前v2的Table A.5仍写Adam与余弦LR，Table A.1/A.4仍写10帧本体观测历史。
- 官方README命令实际默认读取单条lafan_run1_subject5，actor_obs=rep_state、history_length=1；它不是40条LAFAN或13万条BONES的完整实验配置。
- 代码支持motion/velocity多个encoder，但默认slot_mix为motion=1、velocity=0，默认velocity路径和辅助BC不实际训练，不能把它解释为当前默认模型的性能优势。

因此，要获取“产生论文成绩的配置与权重”仍需进一步定位；不能通过日期倒推某个历史commit就是论文版本。

## 5. 官方“完整复现”目前缺哪些材料

| 项目 | 当前可确认状态 | 对后续工作的影响 |
|---|---|---|
| 核心训练、WM/策略代码 | 已公开，Apache-2.0 | 可直接学习和建立独立官方源码栈 |
| mjlab_research依赖 | README指定地址返回404，Issue #1仍开放 | 当前安装路线存在实际阻塞 |
| 普通公开mjlab替代 | 本次检查的公开版本缺研究接口 | 不能直接改路径后宣称官方等价 |
| 完整论文run config | 未在当前README/发布入口定位到 | 需要明确repr、actor观测、数据、种子、超参与checkpoint对应 |
| 数据清单/预处理 | 未在主仓库定位到论文筛选后精确成员清单与完整脚本 | 当前130394条不能直接当作者129514条 |
| 论文完整评分入口 | benchmark.py是吞吐测速；play.py是交互回放 | 需要作者评分脚本或语义明确的最小适配 |
| 完整训练checkpoint | README/Release未定位到主成绩对应的完整训练状态与run配置 | W&B接口存在不等于已取得相应权重；网页demo资产不等于完整训练包 |
| 恢复续训 | 当前保存WM/Actor/Critic权重；warm-start入口只载入WM | 不能当成三网络、优化器、sampler、RNG的完整resume |
| 双GPU主成绩 | 论文有；当前源码未发现相应分布式训练入口 | 后续另核，第一阶段先单卡 |
| 速度接口完整论文实验 | 当前主要是运动跟踪目标下的多encoder支持 | 不能视为已含论文独立速度reward/终止/critic的全部RL实验 |
| ONNX导出 | 已有exporter | 不等于本项目已具备完整G1实机部署链 |

依赖缺口有具体源码依据。本次检查普通公开mujocolab/mjlab的f389738f68bb831754c030e4ec1d3585b7498cdf：其MotionLoader仅处理单npz，未提供官方SuperMimic用到的motion_ends、root_pos_w/root_quat_w及相应研究接口；MotionCommand也缺external采样模式/set_sampling_distribution。不能仅靠重命名目录解决。[公开mjlab命令实现][MJ-COMMAND]、[官方依赖问题][ISSUE1]、[官方数据/训练入口][O-train]、[官方想象环境][O-wmenv]

## 6. 对差距的判断与后续优先级

可以确定的是：我们重建了论文主算法，并获得可用的LAFAN效果和完整BONES训练/评分能力；但数个未公开细节的独立选择叠加后，已经形成与官方不同的训练系统。现有数据不能把差距按百分比归因到某一项，也不支持把问题全部归咎于显卡或训练时间。

最有解释力、也最应优先按官方整体复现的组合是：

1. 统一动力学积分结构与WM误差度量。
2. 参考预览时间窗与Actor观测信息条件。
3. normalizer、网络结构和对应优化配置。
4. Critic、参考末尾、return sampler和replay的完整语义。
5. 配套仿真依赖、精确数据和完整评测。

单独延长k8到k16只改变模型训练展开长度，无法同时解决以上结构与口径差异。因此建议保留P12为独立实现的备选研究，不把它作为拿到官方代码后的默认下一轮重计算。若外部会话已经启动P12，保留其运行，不由本次文档更新停止任务。

新的O1优先准备完整官方栈，再开展对应的LAFAN与BONES指标复现。官方基线先保留其自身算法，不默认带入713维XYZ反馈、hard配额、存活加权Critic或P11局部高度修正；旧实现作为已有成果和诊断参照保留。

具体接续：[O1准备计划](O1_OFFICIAL_REPRODUCTION_PLAN.md)、[下一轮启动提示词](O1_CODEX_START_PROMPT.md)、[已核实来源清单](../configs/official_source_inventory_20261111.json)。

## 证据索引

下列源码链接固定在本次审查提交，避免之后main更新影响复核。

[U-model]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/supermimic/networks.py
[U-learning]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/supermimic/learning.py
[U-task]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/supermimic/task.py
[U-motion]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/supermimic/motion.py
[U-env]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/supermimic/environment.py
[U-eval]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/scripts/evaluate.py
[U-P6]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/results/20261105-p6-position-feedback-s0/summary.json
[U-P7]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/results/20261105-p7-feedback-reproduction-s0/summary.json
[U-P9]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/results/20261107-p9-critic-full-scale-s0/summary.json
[U-P10]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/results/20261108-p10-8k-hard-practice-s0/summary.json
[U-P11]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/results/20261110-p11-root-height-consistency-s0/summary.json
[U-review11]: https://github.com/kaiwen123-yang/Supermimic/blob/dd28b969e7ab33a3e285f2caa7469e745f7cb5a0/docs/P11_REVIEW_20261111.md
[O-rep]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/representations.py
[O-gen]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/utils/gencoord_helpers.py
[O-wm]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/learners/wm_learner.py
[O-policy]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/learners/policy_learner.py
[O-wmenv]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/envs/world_model_env.py
[O-model]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/models.py
[O-opt]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/learners/learner_utils.py
[O-runner]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/runners/supermimic_runner.py
[O-sampler]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/runners/reset_sampling.py
[O-reward]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/utils/tracking_reward.py
[O-train]: https://github.com/HybridRobotics/supermimic/blob/5efbf114e11f725c31d83e217be987c13c0e4ce2/src/supermimic/scripts/train.py
[O-muon-commit]: https://github.com/HybridRobotics/supermimic/commit/0e5ff6bb00166fdbdb308ce23583f55948504fac
[O-ln-commit]: https://github.com/HybridRobotics/supermimic/commit/aec4a5e4ba15c93c2b214e6cbb939613e50d2e64
[MJ-COMMAND]: https://github.com/mujocolab/mjlab/blob/f389738f68bb831754c030e4ec1d3585b7498cdf/src/mjlab/tasks/tracking/mdp/commands.py
[ISSUE1]: https://github.com/HybridRobotics/supermimic/issues/1
[PAPER]: https://arxiv.org/pdf/2610.28480v2

