# P10 Codex 启动提示词

本文件是下一次在 D57 执行 P10 的提示词。发布本计划时，P9 已完成，P10 尚未实施或启动。

将以下整段交给能连接 `autodl-d57` 的 Codex：

```text
继续 kaiwen123-yang/Supermimic。先读取最新 main 的 AGENTS.md、docs/P9_REVIEW_20261108.md、docs/P10_8K_HARD_PRACTICE_PLAN.md、configs/next_stage_8k_hard_practice_protocol.json 和 configs/p10_hard_motion_set.json，再结合P9结果完成必要适配并执行P10。P9三路已经结束，不重新启动P9。LAFAN回报>=.82已被用户认定复现成功，不撤销，不另加验收门槛。

使用autodl-d57现有环境和G1资产，在 /root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice 独立源码工作树完成工作。保留原项目未提交改动、已有工作树/Git/stash与其他项目。禁止setup、安装升级或重建环境。

本轮campaign=20261108-p10-8k-hard-practice-s0。两路full8k_control / full8k_hard_practice都从P9完整库checkpoint_0009000.pt完整resume三网络、三Adam、sampler、已保存RNG、iteration9000、actor_updates8995及原全局LR，不只迁移网络，不重置采样历史，不再做5轮WM-only。父路径以P10协议为准。每路8192真实环境、8192 imagination、WM10×4096，H32/k8、replay1000、Critic5×4、原713/.5配方和survival_weighted不变，不自动提高LR。

两路来源均LAFAN2048/BONES6144。control reset=LAFAN2048+完整BONES6144；candidate reset=LAFAN2048+完整BONES5120+固定hard1024。hard为冻结639条Stunts或名称含flip/side_roll/cartwheel/handstand的并集；general仍包含全部hard。source只有两个，reset stratum可有三个；共享已恢复G/M，池内条件归一化。原record的两来源memory EMA每来源只更新一次，不把重叠hard池加入EMA更新循环。原BONES source_clip_id按现有联合manifest映射，不重新编号或复制数据。

共同复用P9同一底层CPU只读memmap，43帧参考窗口；不重新筛选/下载/转换/打包约45GB参考库。首路正常初始化并填充一次64步replay后进入联合训练，即接入第二路；此后两路独立tmux并行。训练各Torch2线程，有实际任务的CPU统计最多12个单线程worker。用普通运行节点记录GPU实际占用和主机内存，不另做容量/吞吐试验。

每路新增18000联合更新9001–27000，或累计新阶段40h先到；父历史成本单列，实际恢复继续累计新阶段已用时间。单个Codex交互窗口<=4h，后台tmux跨窗口持续，不因交接停训/重建replay/重置LR。

全BONES正式评分在15000/21000/27000；LAFAN保持在12000/15000/18000/21000/24000/27000；时间先到在实际终点补两项。按iteration-9000排程，父9000评分复用。全库评估按(reference_steps, original_source_clip_id)组批，默认1024，保持每条从0至原终止/自然末尾的评分；输出恢复原ID顺序。失败尾窗按原ID选择各既定组最小两个，最多8，不因长度排序改选样规则。所有正式GPU评分、六个小WM证据和Git发布共享协议中的现有唯一锁，训练不占锁。

只补计划指定六个现有P9 full9000失败短窗的同动作WM递归预测，复用真实状态、实际action、previous_action和context33，不新跑物理、不扫起点。正常训练顺带记录LAFAN/hard/其余BONES的真实transition/reset、WM有效窗、Actor起点、hard clip/bin覆盖和已有forward分组误差。每千轮原有最多4条selected rollout的sidecar补实际optimized/raw/weighted/Smean，不新增forward/backward或梯度扫描。

按计划比较固定终点/共同节点的全库R、body-orientation与共同成功集合质量、hard技能及LAFAN保持。负面结果也发布，不挑最佳节点或拼接各checkpoint成功。全部BONES逐clip标量用CSV每1000条分片，附一次schema、索引和小summary；完整40条LAFAN评分照常。推代码、实际配置、指定小证据、紧凑统计和真实结论到GitHub。大checkpoint/全轨迹/视频/日志留服务器；推完不在我电脑归档，不Release、不tar、不自动阶段清理。原checkpoint每轮保存与最近20次滚动/里程碑保留照旧。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、benchmark及无关工作。直接做本轮所需适配和正式训练；遇到真实错误才针对修复。不要新增Critic/H/k/LR/比例扫描、PPO、多seed或实机任务。预算结束完成实际终点评分与轻量发布，报告真实状态，不自动延长或启动P11。

本请求授权实施上述P10计划和两路正式训练，不要停在计划说明或反复询问启动许可。先完成必要适配，记录实际启动状态；每个交互窗口结束给出tmux/run/最新iteration/已用阶段时间/待评分发布节点及下一窗口接续方式，保留正在运行的进程。
```
