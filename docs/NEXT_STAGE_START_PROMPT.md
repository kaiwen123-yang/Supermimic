# P7 启动提示词：巩固已达标模型，并行固定配方从零训练

P7已完成训练、正式评分、关键证据和轻量发布。先读results/20261105-p7-feedback-reproduction-s0/summary.json。下文保留授权范围；接续已有tmux，不重复启动、不重建replay或重置LR，不自动扩预算或开P8。

**用户最新验收口径：达到作者对应实验指标即算该项复现成功；当前LAFAN1已成功。P7是达标后的巩固与研究，不作为成功前置条件。**

完整依据见[P7计划](P7_CONTINUATION_AND_FRESH_PLAN.md)和[执行协议](../configs/next_stage_reproduction_protocol.json)。协议不是直接传给train.py的训练配置。若接续时同名P7进程已经启动，继续它们，不重复启动。

~~~text
请接管 kaiwen123-yang/Supermimic，执行P7。先读最新AGENTS.md、docs/P7_CONTINUATION_AND_FRESH_PLAN.md、configs/next_stage_reproduction_protocol.json，以及results/20261105-p6-position-feedback-s0/的summary.json、conclusion.md、review_20261105.json和b25000_to_b26000_analysis.md。P6已完成，不重跑。完成必要运行/发布适配后直接开始约定正式任务，按节点推送关键结果，不止于重写计划。

用户已确认：追上作者对应实验指标即可认定该项复现成功，当前LAFAN1已成功。不要追加40/40、从零重训、更多seed、H100同等耗时、BONES或实机作为当前验收门槛。按既定P7预算开展达标后的研究，已有B33000达标结论不因新节点回撤而撤销。

当前已达到的成果是P6 B33000：回报0.86624655、37/40、父34成功全部保留，共同完整31动作XY约0.064m。后续研究保持/困难动作与从零学习成本，不改动已经有效的713输入、半ActorLR及完整联合算法，不把40/40冒充论文已有达标门槛。

使用autodl-d57，一个工作树：
/root/autodl-tmp/robot-repro/supermimic-p7-reproduction
复用正常.venv、G1资产、processed动作缓存，保留原工作树和未提交改动。不安装升级、不重建环境、不重做retarget，不动其他项目。

campaign：20261105-p7-feedback-reproduction-s0。并行两个研究任务，不作同初始化A/B胜负比较：

1. continuation：从
/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/outputs/runs/20261105-p6-position-feedback-s0-root_position_feedback/checkpoint_0033000.pt
恢复Actor/WM/Critic、三套Adam、sampler、已保存Torch/CUDA RNG与全局日程，33001–42000，新增9000联合更新。父评分直接用已发布B33000 evaluation.json，37成功/3失败，不重评估父版本。父输入已经713，不重复710→713扩列。

2. from_scratch：同一713/.5有效配置，seed0，无父checkpoint，不传--resume，不载入父网络/Adam/sampler/RNG；全部713输入权重按现有初始化规则新建。迭代1–9000，保持原前5轮WM-only，之后8995次Actor/联合更新，LR从迭代1开始。不能继承父的累计时间或37成功保持字段。

两支各初始填充一次64步replay，新阶段各最多16小时，评估/发布另计。保持4096环境、k8/H32、aux_bce、analytic_smooth温度.05、70维state mean、公共goal710、Actor713/scale.3、Actor LR scale.5、WM/Critic原基础2e-4与250k余弦、原奖励/物理终止/PD/采样/噪声/随机化。每轮始终真实采样→WM拟合→Actor/Critic；从零前5轮按原约定仅WM。

利用96GB显存和25核CPU，两路GPU训练并行，独立run/tmux/log，各Torch2线程。正式全40评估、下述六个小WM预测和Git发布共用work/p2-publication.lock，总并发1；评估Torch2线程。最多4个CPU进程读取明确指定的已有NPZ和日志。预计训练约10–12小时，16小时为各自上限。单个交互窗口≤4小时，tmux后台跨窗口继续，不重启replay/LR，不停止其他项目或为占满资源增开实验。

必要适配：
- 创建两个实际配置和薄P7启动/收尾；按job处理不同起点与节点，不能复用P6同父同终点的A/B胜负逻辑。
- P7显式进入现有紧凑多run发布；有父才compare_to_parent，无父不调用，不读取旧默认父路径。cfg.get的默认表达式不得急求值不存在的protocol[parent]。fresh previous_elapsed_seconds=0，不标恢复状态、不列不存在的parent文件。
- training_summary按真实预热语义统计：WM/采样/计时用所有行，Actor/Critic/imagined指标仅用实际策略更新行，首块995次Actor、全段8995次；不把缺项填0。
- failure_windows覆盖实际全部失败，去掉旧起身/跑步过滤。
- 新评估不再把全轨迹mean误命名为before_failure；保留准确mean，末帧值从真实末帧另给。
- 汇总节点只保留reward分解均值与原evaluation路径，完整40动作在各自evaluation，不把per_motion在多个层级反复复制。

主续训每1000轮完整评估34000–42000，固定42000/末三40000、41000、42000；报告父37保持、三原失败、全部回报/完成、起身/跑步身份、奖励质量和同完整集合XY/姿态。from_scratch每1000轮评估1000–9000，固定9000/末三7000、8000、9000，报告首次已评估≥0.82节点及真实从零耗时和后续保持；未达到就如实交付曲线，不自动延长。不得挑最好checkpoint替代终点，不拼接动作、不改变评分。

同时按协议补传分析所需有限数据，不阻塞正式训练：
- P6 B33000三个实际失败各2.64秒真实短窗：dance1_subject1 104.48–107.12、fallAndGetUp2_subject2 139.36–142.00、jumps1_subject2 230.06–232.70；起身用B30000、跳跃用B32000同参考时间成功短窗，共5窗。
- 每窗保留完整qpos/qvel、参考、action/previous_action、reward和8项、frame/dt/context及坐标来源，小NPZ+可读JSON进Git；完整原始轨迹留服务器。原状态含初始帧，action[k]产生state[k+1]。
- 仅B33000 WM，对三失败各取tf−1.28s、tf−.64s两个真实起点，喂已记录动作展开32步，共6窗。初始previous action用action[i−1]，比较实际state[i+1:i+33]，发布8/16/32步误差、reward、analytic_smooth概率及短预测数组；不是新物理仿真或Actor闭环回放。
- B31000四个主要回撤与B30000同参考时间成功窗按协议精确索引提取；30001–31000已有日志只取Critic MSE最大与Actor裁剪前norm最大更新各±10行、重叠合并。不要重复已完成25k→26k分析，不加载旧模型追溯不存在的replay。

正式训练日志复用现有H32计算，增加Eq2短期reward和terminal bootstrap两块均值、V_H/λtarget均值与极值、survival。主续训每千轮只保留最大Critic MSE更新中最多4条按最大|λtarget−旧V|选出的原有rollout小记录，按计划导出；从零只保留标量与局部日志。不新增forward/backward、梯度扫描、参数全量复制或RNG采样，不用这些统计裁剪/拒绝/回滚更新。大裁剪前norm不是实际Adam步长；所选样本也不是已证明的最大Actor梯度来源。

顺序：完成对应计算/正式评分→推代码、实际配置、完整40动作/逐回合JSON、紧凑区间统计、指定短窗/预测/局部日志与结论→继续既定研究。新的少量证据数组允许进Git。大checkpoint、完整视频、完整轨迹/数组、缓存和完整日志留服务器，不上传Release、不入后台大文件队列、不打包、不在我电脑归档。我自行备份并统一删除，助手不自动阶段清理或标已备份。原每轮checkpoint、最近20轮滚动及父/里程碑/最终保留照旧。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、额外benchmark、120起点扫描和通用框架。遇到真实正式运行错误再定点修复。两任务到约定迭代或各自时限后完成正式评估、关键证据推送和真实结论，给出GitHub链接及服务器产物位置；不等待批量视频/用户备份，不自动扩预算或开P8。
~~~
