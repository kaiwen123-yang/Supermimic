# P11 full8k_residual_control 实际结果

实际终点 36000，计划36000或累计新阶段20h；本阶段联合更新 9000 次，用时 13.6213h。完整恢复P10 hard27000，前序 106.1178h 单列。

| 集合 | 完整 | 回报 | body orientation贡献 | 缺失尾段 | 执行质量缺口 |
|---|---:|---:|---:|---:|---:|
| all_clips | 129152/130394 | 0.86375135 | 0.13337332 | 0.00539350 | 0.13085514 |
| fixed_hard | 312/639 | 0.44230236 | 0.05999134 | 0.36169374 | 0.19600390 |
| other_bones | 128840/129755 | 0.86582685 | 0.13373470 | 0.00363884 | 0.13053431 |

LAFAN保持 29/40，R=0.73313568。起身/跑步及父33成功保持身份见逐节点comparison.json。

| 名称技能 | 完整 | 回报 |
|---|---:|---:|
| flip | 0/44 | 0.32126085 |
| side_roll | 20/22 | 0.57187067 |
| cartwheel | 90/120 | 0.52746100 |
| handstand | 0/160 | 0.05874825 |

全库正式节点 [30000, 33000, 36000]；末三可用 [30000, 33000, 36000]，均值 0.8634922482975024。共同完整集合的XY/SO3/body/joint与奖励分解、hard实际曝光和分组WM误差见逐节点comparison与paired_comparison。

结果同时覆盖困难技能、普通动作姿态质量和LAFAN保持；不以完整数或训练loss替代控制质量，不挑最佳节点、不拼接成功。不同replay分布的WM误差不作同输入因果比较。

大产物保留 /root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency/outputs/runs/20261110-p11-root-height-consistency-s0-full8k_residual_control；不Release、不tar、不在用户电脑归档、不自动清理或延长、不启动P12。
