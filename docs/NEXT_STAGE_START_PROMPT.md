# P5 启动提示词：两组完整联合续训，关键结果优先

> 执行状态：P5已于2026-11-04 19:00启动。下文为原启动指令；交接不得重复执行启动、停止或重启训练。先读 results/20261104-p5-actor-stability-s0/summary.json 和服务器现有进程。

计划日期：2026-11-04（北京时间）。本文件发布时P5尚未实施或启动；最新完成阶段为P4 C0-18000。

将下面全文交给执行端Codex。完整依据见[P5计划](P5_STABILITY_PLAN.md)及[执行协议](../configs/next_stage_stability_protocol.json)；协议不是可以直接传给train.py的训练配置。

~~~text
请接管 kaiwen123-yang/Supermimic 并执行P5。先读取最新AGENTS.md、docs/P5_STABILITY_PLAN.md、configs/next_stage_stability_protocol.json，以及P4 summary/comparison/training。已有P4完成到18000；不要重复P4。此次要完成必要适配、启动正式训练、按节点评估和推送关键结果，并交付最终分析。

在autodl-d57使用一个P5源码工作树 /root/autodl-tmp/robot-repro/supermimic-p5-stability，复用现有.venv、G1资产和processed动作缓存，保留所有已有工作树和未提交改动。父权重直接使用：
/root/autodl-tmp/robot-repro/supermimic-p4-c0/outputs/runs/20261103-c0-continuation-s0-h32_aux_bce/checkpoint_0018000.pt
父评分使用仓库已发布的18000 evaluation.json，不重放父模型，不重建环境或下载历史归档。

两组从同一父模型的Actor/WM/Critic、三套Adam、sampler和已保存Torch/CUDA RNG恢复；各初始填充一次64步replay，全局迭代从18001继续。A c0_control保持当前全部算法；B actor_half_lr只将Actor学习率乘0.5，WM/Critic仍按原2e-4基础LR与250000轮余弦日程。请在set_schedule每一轮应用actor_learning_rate_scale=1.0/0.5，不能只改初始化，也不能把公共learning_rate减半。日志记录真实三组LR。两组始终完整执行真实采样→WM拟合→Actor/Critic，保持H32/k8、aux_bce、robot_root710维、原奖励/终止/PD/采样器/噪声/随机化，保留Adam和全局LR进度。

每组新增6000联合更新，目标24000，新阶段各最多16小时（含自身一次replay填充，旧累计耗时不用作预算）。两路GPU训练尽可能并行，各独立run/tmux/log；同一个源码工作树共享原publication锁，使正式40动作评估和Git发布总并发为1。每1000新增轮评估19000至24000，时间先到则发布真实非整千终点，不自动补预算。单个Codex交互窗口≤4小时，后台跨窗口持续运行，交接不停止/重启训练、不重建replay。

做有限脚本适配后直接正式训练：两份继承配置、薄P5启动/收尾入口；发布从P5配置读取18000父评分/父路径，分母32成功/8失败，summary与索引按arm隔离。现有P4发布有9000/29/11及单run硬编码、累计metrics.jsonl上传，必须适配。复用现有评估/统计/锁，不运行旧P3/P4收尾main，不建新调度或监控框架。

同时用最多4个CPU工作进程读取P4已保存评分NPZ：dance1_subject1的18000与14000约104–107.1秒；三个最终失败起身分别对12000/14000成功轨迹的同参考时间。查看参考和实际高度/倾斜、速度、动作及偏离起点，注意状态数组含初始帧。只读已有轨迹，不重新仿真，不让这项分析阻塞正式训练。提交小型关键事件/数值与解释，原始数组不转成大JSON。

结果使用同一checkpoint完整40动作评分。固定比较最终24000及末三共同节点22000/23000/24000，报告回报、完整数、六起身身份、跑步4/4保持、父32条成功保留/退化、新增和三节点都成功的交集。缺失节点如实记录。不能拼接逐动作最佳版本或只挑最高分，不能把半LR假设写成已证实根因。最终XY比较用18000/A/B都完整成功的同一动作集合。

发布顺序是完成计算/正式评分后，先推源码、实际配置、完整40动作评估JSON、每1000轮关键统计、必要失败证据与结论，然后继续研究。完整逐轮日志、大checkpoint、完整视频、原始数组/轨迹、缓存均留服务器，不上传Release，不入后台大文件队列，不打包，不在我电脑额外归档。由我定期备份并统一删除，助手不自动删、不自行标已备份。原每轮checkpoint、最近20轮滚动保留及父/整千/最终权重保留规则照旧。

禁止防御性编程及单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、额外benchmark；遇到真实运行错误才针对修复。不要安装升级环境、不要动其他项目任务。两组到既定更新数或各自时限后，先完成正式评分和关键结果推送，再交付A/B结论、GitHub链接、服务器产物位置和下一步建议；不等待批量视频/用户备份，不自动开启新实验。
~~~
