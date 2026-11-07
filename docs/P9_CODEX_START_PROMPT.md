# P9 Codex 启动提示词

实际状态：P9已实施，先读results/20261107-p9-critic-full-scale-s0/summary.json并检查现有tmux，不要再次运行start_p9.py。
继续 kaiwen123-yang/Supermimic，直接实施已授权P9并启动正式训练。先读AGENTS.md、docs/P8_REVIEW_20261107.md、docs/P9_CRITIC_AND_FULL_SCALE_PLAN.md、configs/next_stage_critic_full_scale_protocol.json。P8已经完成，不重复启动。当前仅发布了P9计划，执行端适配尚需完成。

目标：保留H32，处理已观察到的终止后Critic污染；稳定性对照与修正后的BONES完整库训练并行。效率专项后置。D57是96GB显存、25vCPU，复用现有独立环境/G1资产，不setup、升级、重建或清理正常环境，不影响其他项目。

1. 两路LAFAN均从P8 H32-51000完整恢复三网络、三套Adam、sampler、已保存Torch/CUDA RNG和全局LR。A保留原无权重Critic；B仅将Critic loss改为mean(detach(S_t)*(V-Rlambda)^2)/mean(detach(S_t))。S_t为当前transition前累计存活，全rollout均值只算一次，首次终止transition仍计入。自然终点沿用frame+step+1>=lengths[clip]-1，不把训练500步timeout新增为想象终止。Actor目标、λtarget、k8/H32、713/.5、奖励/物理终止/PD/采样不变，不加epsilon/硬阈值/value clip。各51001–60000或累计新阶段16h，每1000轮全40评分，父基线37，尾三58000/59000/60000。正常同一次forward记录raw与weighted损失及零存活后缀贡献，不另跑推理或测试。

2. 同时16个单线程CPU worker修正BONES筛选：高处/穿透改用所有non-world机器人body origin的最低z；浮脚仍用foot碰撞几何对地距离。名称规则补论文公开外部支撑/地形项，参考SONIC官方词表但保留平地flip/side-roll/cartwheel/handstand，避免裸box/climb误删boxing/mountain_climber。冻结规则并记录匹配原因，不凑作者计数、不按训练失败删数据。
复用P8已下载metadata/CSV/正确NPZ；旧已接受候选只重算必要FK筛选，所有新名称规则允许而没有有效NPZ的候选才从已有CSV补转换，包括此前被旧名称或物理规则排除的候选；重新考虑全部原始metadata。旧清单和成绩不覆盖，不重下载或全量推翻正确转换。

3. 完整修正库就绪后立即接第三GPU任务，不等待两路胜负。第三路从同一H32-51000仅迁移三网络权重，新建Adam、联合sampler/replay/RNG和阶段计数；H32+存活加权Critic，1–9000或累计16h，前5次WM-only。4096环境固定1024 LAFAN、3072 BONES，各来源内按原50/40/10 reset分布。共享同一个策略/WM/Critic，记录实际各来源训练份额；这不是纯BONES或从零3h复现。

4. 第三路完整参考存CPU连续数组/只读memmap，按阶段搬GPU窗口：Actor H32加未来goal10共43帧约170MiB；WM/真实采集/完整评分同样按需取窗口。参考可预取，robot_root goal必须每步在GPU用预测根旋转可微构造。不能把完整参考同时复制到训练与评分GPU，不建通用缓存框架或benchmark。

5. 第三路更新前保存固定初始化checkpoint0；在0/3000/6000/9000及实际终点评分全部修正后BONES动作，3000/6000/9000同时评估LAFAN40保持，0点LAFAN复用同权重父评分。BONES和LAFAN两种评分都显式选择各自子库，记录联合训练与实际评估定义，普通同数据resume约束保留；两数据集分开报分。冻结约40h监测清单，从同次全库结果提取统计，不另跑子集评估。特别报告flip/side_roll等技能与body-orientation质量，不能用总成功率替代。

6. 从已有正式轨迹仅补两个成功短窗：H16-50000 dance1_subject1的104.50–107.14s；H32-49000 fallAndGetUp1_subject1的6.70–9.34s。对应H32-51000失败窗已存在，复用。正常训练每千轮最多4条小rollout，记录S_t/自然终点/来源/剩余步分组，不增加forward/backward、梯度扫描或起点扫描。

7. 目标同一GPU三个训练进程并发，各Torch2线程，数据默认16 worker、纯数据条件可20。正式评分/指定GPU证据/Git发布统一使用：
/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock
总并发1，正常训练不占锁。独立tmux/run/log，单Codex窗口≤4h，后台持续运行；不停止其他项目。

8. 每路初始64步replay填一次；活跃tmux交接不重启replay/LR。实际进程错误后恢复才作必要填充，已消耗P9预算继续累计，重启不重新给16h，不做恢复演练。

9. 先推GitHub：代码、实际配置、数据定义/过滤统计、全部逐clip评分、紧凑统计、指定小数组、真实结论和服务器路径。全库逐clip指标按2000条紧凑CSV/JSONL分片并附小summary，避免巨大单JSON难以读取。大权重/全轨迹/视频/缓存/大日志留服务器；不Release、不打tar、不在我电脑归档、不自动清理。

严禁防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、无关监控和benchmark。不要顺手改采样Gmax/timeout/LR/reward/成功标准，禁止无关H/PPO/多seed/实机扩展。发生真实运行错误才针对修复。

先汇报真实已启动tmux/run与每条线状态，按计划持续执行。预算结束完成正式评分和轻量发布，不自动延长或开P10。候选loss变小不代表控制进步，以全动作回报、父成功保持、末三及困难技能质量判断。
