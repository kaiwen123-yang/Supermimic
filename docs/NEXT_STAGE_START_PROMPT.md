# P6 启动提示词：当前相对根位置反馈，两支联合续训

P6已完成本段训练、正式评分和轻量发布。先读取results/20261105-p6-position-feedback-s0/summary.json和conclusion.md；以下为本段历史启动词，不重复执行，不自动开启下一阶段。

将下面全文交给执行端Codex。[P6计划](P6_POSITION_FEEDBACK_PLAN.md)说明依据与具体实现；[执行协议](../configs/next_stage_position_feedback_protocol.json)不是直接传给train.py的训练配置。若后续交接时同名P6任务已启动，接续现有进程，不重复启动或重建replay。

~~~text
请接管 kaiwen123-yang/Supermimic，执行P6当前相对根位置反馈实验。先读最新AGENTS.md、docs/P6_POSITION_FEEDBACK_PLAN.md、configs/next_stage_position_feedback_protocol.json，以及results/20261104-p5-actor-stability-s0/下的summary.json、conclusion.md和review_20261105.json。P5已经完成；不要重跑。完成必要代码适配后直接开展约定正式训练/评估，按节点推送关键结果并给出最终分析，不止于写计划。

在autodl-d57使用一个源码工作树：
/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback
复用现有.venv、G1资产、processed动作缓存，保留原工作树和未提交改动；不要安装升级或重建环境，不动MPC-RL/π系列及其他项目。

两支都从P5 B24000恢复：
/root/autodl-tmp/robot-repro/supermimic-p5-stability/outputs/runs/20261104-p5-actor-stability-s0-actor_half_lr/checkpoint_0024000.pt
父评分直接使用已发布的：
results/20261104-p5-actor-stability-s0-actor_half_lr/milestones/iteration_0024000/evaluation.json
父基线是34成功/6失败、回报0.755425，不再使用P4的32/8。不重放父checkpoint，不下载旧归档。保留P5 A24000及其6/6起身轨迹作解释参考，不拼接策略。

campaign为20261105-p6-position-feedback-s0。A no_position_feedback正常续训、Actor encoder710维；B root_position_feedback仅增加当前相对根位置3维，encoder713维。两支actor_learning_rate_scale均为0.5，仍在每轮set_schedule应用；WM/Critic保持原基础2e-4、250000轮余弦及全局进度，不改公共LR。配置记录actor_root_position_feedback=false/true及actor_root_position_scale_m=0.3。

误差统一为：
inverse_full_robot_root_rotation * (current_reference_root_position - current_robot_root_position) / 0.3。
使用当前帧和完整根四元数，不用下一帧、仅yaw、绝对世界XYZ或十帧各加XYZ。不新增clip、噪声或可学习归一化。保留公共MotionLibrary.goal710维，只在Actor encoder入口拼接，Critic仍收原710维及已有privileged相对位姿；历史930维、latent32、隐藏层、decoder、WM与replay表示均不变。

真实collection、每一步H32 imagined rollout和正式evaluate使用同一特征函数。想象过程中由该步预测state重新计算，保留位置和四元数梯度，不detach、不固定用rollout起点。评估按checkpoint config构造正确Actor。反馈组正常路径显式传入误差，不以缺参数时悄悄补零代替实现。

仅B首次从旧710父模型恢复时，把encoder.0.weight原2048×710保留，末尾加3列零；找到已保存Actor Adam param_groups[0]["params"][0]对应状态，把exp_avg、exp_avg_sq也加3列零，保留step和所有其他矩状态。其余Actor/WM/Critic、三套Adam、sampler、Torch/CUDA RNG与全局轮数均继承，不重置Actor或Adam。从自身713checkpoint恢复不重复扩列。该迁移由数学结构保证初始映射，不增加等价推理、哈希或其他测试。

两支各初始填充一次64步replay，全局24001–33000，新增9000次完整联合更新；每支新阶段最多16小时，含这一次填充，旧累计耗时单列，正式评估/发布另计。每轮完整执行真实采样→WM拟合→Actor/Critic，保持4096环境、k8/H32、aux_bce、analytic_smooth温度0.05、70维state mean、原奖励/物理终止/PD/采样器/噪声/随机化。不要增加其他算法差异。

利用96GB显存和25核CPU并行两路GPU训练，各独立run/tmux/log，训练各Torch 2线程。正式40动作评估和Git发布共享同一个work/p2-publication.lock，总并发1，评估Torch 2线程。最多4个CPU进程读取有具体问题的已保存轨迹；不为占满资源添加实验或benchmark，不停止别的项目。按P5双跑实测，9000更新预计训练约10–12小时，16小时为上限而非必须跑满。单个Codex交互窗口≤4小时，后台跨窗口持续；交接不停止/重启训练，不重建replay、不重置LR。

必要适配包括两份继承配置、薄P6启动/收尾入口。publish_checkpoint.py当前只识别P5协议路径才进入按arm隔离的紧凑发布，必须让P6显式复用该分支，避免回退到累计metrics.jsonl上传/单campaign覆盖。复用P5聚合但改父24000、动态34/6、节点25000–33000、tail31000/32000/33000和位置反馈结论。不要执行旧P3/P4/P5启动main或旧大包收尾，不复活diagnose_checkpoint的120起点扫描，不建通用框架。

每1000新增轮评估同一checkpoint的全部40条完整动作，保存25000至33000九个节点。固定终点33000和末三31000/32000/33000；时限先到则发布真实非整千终点，比较共同完成迭代并说明不等进度。不挑最好checkpoint代替最终，不拼接动作。保持原reward和终止，不放宽标准。

报告全40回报/完成比例/完整数、六起身与四跑步身份、父34条保持/退化/新增、末三成功交集与回报均值/范围。用现有reward component sums计算八项贡献和1−R=(1−C)+(C−R)，重点比较root position。位置精度比较使用父B24000、A最终、B最终都完整成功的同一集合，列名字、数量、逐动作XY和均值，同时保留全40结果。位置反馈是本项目假设，不冒充作者未公开的goal；单次超过0.82不等于整篇论文复现。

在不阻塞训练的情况下，优先复用已发布failure_windows。需要时间演变时才读取P5已有NPZ：三条大漂移动作fightAndSports1_subject4/dance2_subject5/dance2_subject4；dance1_subject1约107秒翻转；三个B失败起身与A24000成功轨迹的同参考时间。只交付少量事件/数值与解释，状态数组注意初始帧，不重仿真、不重复旧P4分析、不扫额外起点。P5没有新同动作WM预测，不能拿P4旧误差当B当前误差。

发布顺序：完成节点训练/正式评分→推代码、实际配置、完整40动作/逐回合JSON、每1000轮紧凑统计、关键失败证据和结论→继续既定研究。完整逐轮日志、大checkpoint、视频、原始数组/轨迹及缓存留服务器，不上传Release、不进后台大文件队列、不打包、不在我的电脑另做归档。我定期导出至存储盘备份并统一删除，助手不自动阶段清理、不自行标已备份。原每轮保存、最近20轮滚动及父/整千/最终checkpoint保留规则照旧。

禁止防御性编程和单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、额外benchmark；遇到真实正式运行错误再针对修复。两支到更新数或各自时限后，完成正式评估和关键结果推送，交付真实结论、GitHub链接、服务器产物位置及建议；不等待用户备份或批量视频，不自动扩预算或开P7。
~~~
