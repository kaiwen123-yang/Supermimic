# P8 lafan_h16 实际结果

实际终点 51000，目标 51000。完整成功 31/40，全动作回报 0.73023952，完成比例 86.0356%。
本阶段 9000 次训练迭代、9000 次Actor更新，累计本阶段 7.5402h；C42000前序训练 47.1454h 单列。

| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |
|---|---:|---:|---:|---:|
| 43000 | 32/40 | 0.77613330 | 91.9337% | 30/36 |
| 44000 | 32/40 | 0.74526302 | 88.8695% | 32/36 |
| 45000 | 22/40 | 0.56628547 | 74.5284% | 22/36 |
| 46000 | 28/40 | 0.70066470 | 82.8207% | 27/36 |
| 47000 | 32/40 | 0.73655162 | 89.5455% | 31/36 |
| 48000 | 32/40 | 0.77173863 | 91.4802% | 31/36 |
| 49000 | 33/40 | 0.77769940 | 91.1109% | 33/36 |
| 50000 | 30/40 | 0.73679964 | 87.0940% | 28/36 |
| 51000 | 31/40 | 0.73023952 | 86.0356% | 30/36 |

尾节点：{'prescribed_iterations': [49000, 50000, 51000], 'available_iterations': [49000, 50000, 51000], 'mean_return': 0.7482461839607527, 'available_success_intersection': ['dance1_subject3', 'dance2_subject1', 'dance2_subject2', 'dance2_subject3', 'fallAndGetUp3_subject1', 'fight1_subject2', 'fight1_subject3', 'fightAndSports1_subject4', 'jumps1_subject1', 'jumps1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'sprint1_subject4', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk2_subject4', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1'], 'complete_tail_available': True}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。

这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P9。

大产物保留在 /root/autodl-tmp/robot-repro/supermimic-p8-stability-scale/outputs/runs/20261106-p8-stability-scale-s0-lafan_h16；用户备份未确认，不自动清理。
