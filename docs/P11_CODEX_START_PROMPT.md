# P11 Codex 启动提示词

状态：计划已发布，服务器实施与训练尚未启动。P10已完成；不要再次启动P10。将下面正文交给连接 `autodl-d57` 的 Codex，即授权实施并启动本轮两路正式训练。

```text
请继续我的 SuperMimic 独立复现项目，实施并启动 P11，不要只读完计划或再次给我一份建议。

仓库：https://github.com/kaiwen123-yang/Supermimic
服务器：autodl-d57，主项目 /root/autodl-tmp/robot-repro/supermimic。
先读取最新 main 的 AGENTS.md、docs/P10_REVIEW_20261110.md、docs/P11_ROOT_HEIGHT_CONSISTENCY_PLAN.md、configs/next_stage_root_height_protocol.json 和 configs/p11_fixed_real_windows.json，沿用现有 activate.sh、.venv、依赖与G1资产。既有工作树和用户改动保留；新工作树 /root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency。

当前事实：P10两路均27000，正式评分和发布全部完成。control全BONES R=.86659060/129579完整；hard R=.85921480/129516完整，side_roll21/22、cartwheel85/120，但flip0/44、handstand0/160。LAFAN >=.82已经复现成功，不撤销、不新增验收条件。P10有效想象区已有高度/速度不一致证据，但没有证明全部困难失败的唯一根因。

本轮campaign=20261110-p11-root-height-consistency-s0。
两路full8k_residual_control与full8k_velocity_height共同从以下checkpoint完整resume：
/root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice/outputs/runs/20261108-p10-8k-hard-practice-s0-full8k_hard_practice/checkpoint_0027000.pt
恢复三网络、三Adam、sampler G/M、已保存Torch/CUDA RNG、iteration27000、Actor26995、真实收集计数461586432和全局LR；父已知训练墙钟382024.04194731265秒单列。

唯一算法变量是 world_root_height_mode：
- control=residual，保留现有自由root dz。
- candidate=velocity_trapezoid，只将root高度改成 z_next=z+.01*(vz_current+predicted_vz_next)。predicted_vz_next来自同一次WM前向，不能用真实或参考未来速度。XY、旋转、关节、全部速度、70输出、参数形状和Adam状态均保留；旧dp_z槽保留但不进入候选z。保存并在正常训练及证据加载时使用同一mode。它是研究约束，不能宣布为作者公式或已证明修复。

两路均8192真实环境/8192 imagination/WM10×4096，k8/H32、survival_weighted Critic、aux_bce、原LR与其他配方保持。两来源LAFAN2048/BONES6144，reset为LAFAN2048/all-BONES5120/hard1024；原hard639仍在all池内，共享G/M，不重复source EMA。继续共用P9底层CPU只读memmap，不重筛、重转、重pack或复制完整库。

每路只新增9000联合更新，27001–36000，或累计新阶段20h先到即止。新进程仅一次必要64步replay填充，不加WM-only。全BONES与LAFAN共同正式节点30000/33000/36000及实际终点，父27000评分复用。不同时间上限终点分别报告；同更新比较用已有共同正式节点。沿用1024评分batch、长度排序、完整clip定义与CSV轻量发布。没有自动加预算或开下一阶段。

正式启动前，用原父hard27000 WM对configs/p11_fixed_real_windows.json冻结的7条现有真实失败窗各做一次32步同动作预测，使用已有action/context，不运行新物理或扫描起点；终点两WM各对相同输入再做一次。总21条短rollout/672预测步。父证据先发布/记录，不等又训完才查当前模型；按固定配方继续，不临时加窗口或扫参数。

只在正常collect/k8/H32已有张量中附带计划指定的分组高度-速度残差、真实z/vz/SO3误差和hard bin的真实/WM/Actor起点计数；设备端累计，按原节点推紧凑数据，不新增forward/backward、梯度扫描或逐帧大日志。候选残差按构造为零，不能以它判胜负；看真实技能、完整回报、共同成功质量、同输入预测误差及LAFAN保持。保留P10 control27000与P9 LAFAN原Critic60000历史锚点，不重评。

尽快进入两路正式并行：先完成首路正常初始化、必要填充并进入联合循环，立即接第二路。各自独立tmux（sm-p11-residual、sm-p11-velocity-height），每训练/评分Torch2线程，有实际CPU汇总任务时最多12个单线程worker。96GB卡P10已实占约89GiB，保持两路8k；不再盲加环境或第三learner。容器RAM上限120GiB，页缓存和宿主内存分清，正常节点记录必要cgroup字段。

评分、指定小证据、Git发布共用原锁：
/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock
总并发1；训练不占锁、不停止其他任务。单次Codex交互<=4h，后台可持续跨窗口；交接不重启进程、不重建活跃replay、不重置LR，不因切窗口重新获得预算。

先完成必要实现，然后直接进行上述正式研究。不做防御性编程及任何单元/mock/冒烟/导入/形状/哈希测试、恢复演练、容量/吞吐benchmark、无关扫描或监控框架；遇到真实运行错误再针对修复。禁止setup、安装升级、重建环境，禁止改其他项目。

按正式节点推代码、实际配置、轻量完整评分、指定小证据、阶段计数和如实结论到GitHub；当前状态从真实末点刷新，别再留下P10那种README未启动或latest_training早期快照误导。大产物留服务器，正常rolling20和里程碑保护照旧；推送后不在我电脑归档、不tar、不Release、不自动阶段清理，不把我自行备份列成你完成研究的步骤。
```

完整执行边界以 [计划](P11_ROOT_HEIGHT_CONSISTENCY_PLAN.md)和[协议](../configs/next_stage_root_height_protocol.json)为准。该提示词不要求在一次4小时交互内训练完20小时；它要求正式任务能够连续执行，并完成规定评分、证据与轻量推送。
