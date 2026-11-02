# P3 v2 启动提示词：原文对齐、H32联合续训

2026-11-02原文复核后修订。本提示词替代上一版默认H16/XYZ三组方案；当前计划尚未启动。

```text
读取Supermimic最新AGENTS.md、README.md、docs/REPRODUCTION_PLAN.md的P3 v2和configs/next_stage_tracking_protocol.json。执行当前两组H32完整联合续训，不执行旧P3 v1默认三组。

当前仍以复现原论文为主线。原文Table A.5训练长度320000，250000只是LR衰减日程；6000轮不是充分收敛证据，但LAFAN到0.82的迭代数未公开，也不要盲跑320000轮。保留P2有效的robot_root和analytic_smooth。H16和新增位置XYZ均后移，不将它们称为已确定的论文修复。

使用autodl-d57现有项目 /root/autodl-tmp/robot-repro/supermimic，source activate.sh。环境、依赖和G1资产原位保留；只取B6000完整权重和40动作工作数据，不恢复全部历史归档。P2现已全部发布清理完成，不重复处理。

从同一B6000网络/优化器/sampler/RNG状态建立新run：
C0 h32_aux_bce：保留现有state loss + learned termination BCE；
C1 h32_state_only：保持解析终止，世界模型训练仅保留原state loss，不计算或反传learned termination BCE。
两组都H32、Actor710维和原Critic输入。显式记录world_termination_loss=aux_bce或none，保留旧实验语义。C1可保留checkpoint中的旧termination模块供加载，但不让其BCE继续训练dynamics。

这是判断额外辅助BCE梯度作用的实验，它可能有益或有害，不能预先写成根因已解决。不要同时把state mean乘70改成sum，作者未公开state/nominal归一；其他网络、reward、物理终止、PD、噪声/随机化、采样器、优化器和LR日程均不变。

两组均完整运行真实采样→WM拟合→Actor/Critic更新。默认独立tmux按C1→C0串行；每组新增3000轮，全局6001–9000，恢复完成后的本段最多4小时，包含64步replay预热，评估/视频/上传另计。修正resume新增计时，旧6.44h不占本段预算；不使用max_iterations=6000造成零更新，不重置全局学习率进度。交互窗口≤4h，交接不断训，不干扰其他任务。

每新增1000轮全40动作评估并发布，最终非整千也发布。主指标按论文完整时长归一化回报和高度/倾斜终止；XY/SO3、四条跑步、六条起身和tracking coverage作为诊断，不能把coverage称论文成功率。最终评分和视频共用一次实际轨迹。

复用已有训练张量记录类别采样份额、失败数与WM分项误差，只分析真实失败窗口。已有阶段耗时显示Actor/Critic阶段约占64%，不另开benchmark或重构框架，不改每轮保存约定。3000新增轮只是阶段观察，不能把阴性结果当充分收敛。后续以实际学习趋势接续有效主线，不自动再开H16、XYZ、PPO、多seed或数据扩展。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、恢复演练、全盘扫描及通用fallback。禁止重装、升级或清理工作环境。

源码/配置/紧凑结果推GitHub；大权重、原始数组、轨迹、视频和日志从D57直传Release，大记录按不超过1GiB分卷。只确认uploaded、名称/字节数/URL，不哈希、不重下载核验。上传完成且无消费者后删除明确实验副本；未上传保留并报告，不在我电脑归档。保护源码、Git/stash、.venv、依赖锁、G1资产、工作树及其他项目。

交付两组真实结果、辅助BCE去掉后是否改善模型及控制、实际更新量/耗时、GitHub链接及清理结果。尚未解释的问题如实报告，不能宣称已恢复作者未公开实现。
```
