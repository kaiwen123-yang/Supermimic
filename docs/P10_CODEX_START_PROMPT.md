# P10 已完成：结果与后续接续边界

完成核实时间：2026-11-10T10:34:21.180563+08:00。两路训练、正式评分、指定小证据与轻量Git发布均完成。

两路均从P9 full9000完整恢复并达到27000，各新增18000次联合更新、0次WM-only更新。训练用时control34.8030h、candidate34.7144h，均在40h上限内；原tmux已正常退出。

| 分支 | 全BONES R/完整 | hard R/完整 | LAFAN R/完整/起身 |
|---|---|---|---|
| control | 0.86659060 /129579 | 0.36908697 /193 | 0.81479628 /36 /5 |
| candidate | 0.85921480 /129516 | 0.42915358 /298 | 0.78821171 /33 /3 |

BONES分母130394，hard分母639，LAFAN分母40，起身分母6。candidate侧滚21/22、侧手翻85/120；control分别8/22、10/120。两路flip0/44、handstand0/160。困难练习有技能收益，但本次全库回报和LAFAN保持仍由control领先。

结果入口：
- results/20261108-p10-8k-hard-practice-s0/summary.json
- results/20261108-p10-8k-hard-practice-s0/conclusion.md
- results/20261108-p10-8k-hard-practice-s0/paired_comparison.json

全部BONES节点15000/21000/27000和LAFAN节点12000/15000/18000/21000/24000/27000已评分发布，六个已有失败窗的同动作WM预测已发布。最终BONES尾窗control8、candidate7；LAFAN失败窗control4、candidate7，均来自同次正式评分。

服务器：autodl-d57；源码工作树 /root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice。原run目录为该工作树outputs/runs/20261108-p10-8k-hard-practice-s0-full8k_control与-full8k_hard_practice，各最终模型为checkpoint_0027000.pt。

本阶段无需继续训练、恢复或重建replay。不得把历史启动提示词作为再次运行start_p10.py的指令；不自动追加预算或启动P11。后续研究需要用户新的明确任务。

大checkpoint、数据、完整轨迹和日志留D57。用户备份未确认；不Release、不tar、不在用户电脑归档、不自动阶段清理。已达成的LAFAN复现验收不因本阶段节点波动撤销。
