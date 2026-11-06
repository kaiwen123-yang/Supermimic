# P8 lafan_h32 实际结果

实际终点 51000，目标 51000。完整成功 37/40，全动作回报 0.86980516，完成比例 96.1647%。
本阶段 9000 次训练迭代、9000 次Actor更新，累计本阶段 10.7251h；C42000前序训练 47.1454h 单列。

| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |
|---|---:|---:|---:|---:|
| 43000 | 36/40 | 0.82772753 | 97.0926% | 34/36 |
| 44000 | 37/40 | 0.87323419 | 98.6286% | 35/36 |
| 45000 | 35/40 | 0.82853096 | 92.7404% | 34/36 |
| 46000 | 33/40 | 0.79981812 | 92.0220% | 31/36 |
| 47000 | 34/40 | 0.84772775 | 96.3576% | 31/36 |
| 48000 | 35/40 | 0.82206076 | 92.4438% | 33/36 |
| 49000 | 37/40 | 0.87236567 | 97.6280% | 36/36 |
| 50000 | 34/40 | 0.83207339 | 92.7876% | 33/36 |
| 51000 | 37/40 | 0.86980516 | 96.1647% | 36/36 |

尾节点：{'prescribed_iterations': [49000, 50000, 51000], 'available_iterations': [49000, 50000, 51000], 'mean_return': 0.8580814051072483, 'available_success_intersection': ['dance1_subject2', 'dance1_subject3', 'dance2_subject1', 'dance2_subject2', 'dance2_subject3', 'dance2_subject4', 'dance2_subject5', 'fallAndGetUp1_subject4', 'fallAndGetUp1_subject5', 'fallAndGetUp2_subject2', 'fallAndGetUp3_subject1', 'fight1_subject2', 'fight1_subject5', 'fightAndSports1_subject4', 'jumps1_subject1', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'sprint1_subject4', 'walk1_subject1', 'walk1_subject2', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk2_subject4', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1'], 'complete_tail_available': True}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。

这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P9。

大产物保留在 /root/autodl-tmp/robot-repro/supermimic-p8-stability-scale/outputs/runs/20261106-p8-stability-scale-s0-lafan_h32；用户备份未确认，不自动清理。
