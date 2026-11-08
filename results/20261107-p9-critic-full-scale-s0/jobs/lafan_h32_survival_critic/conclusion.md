# P9 lafan_h32_survival_critic 实际结果

实际终点 60000，目标 60000。完整成功 36/40，全动作回报 0.84312458，完成比例 92.7859%。
本阶段 9000 次训练迭代、9000 次Actor更新，累计本阶段 12.3708h；H32-51000前序训练 57.8705h 单列。

| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |
|---|---:|---:|---:|---:|
| 52000 | 38/40 | 0.88665001 | 99.2705% | 36/37 |
| 53000 | 35/40 | 0.85429350 | 95.1045% | 34/37 |
| 54000 | 39/40 | 0.87918924 | 99.5367% | 37/37 |
| 55000 | 37/40 | 0.86500980 | 95.9460% | 35/37 |
| 56000 | 36/40 | 0.86418384 | 96.5735% | 34/37 |
| 57000 | 38/40 | 0.88949039 | 99.5112% | 36/37 |
| 58000 | 36/40 | 0.87293078 | 96.3353% | 35/37 |
| 59000 | 39/40 | 0.89541801 | 99.5383% | 37/37 |
| 60000 | 36/40 | 0.84312458 | 92.7859% | 35/37 |

尾节点：{'prescribed_iterations': [58000, 59000, 60000], 'available_iterations': [58000, 59000, 60000], 'mean_return': 0.8704911200372756, 'available_success_intersection': ['dance1_subject2', 'dance1_subject3', 'dance2_subject1', 'dance2_subject2', 'dance2_subject3', 'dance2_subject4', 'dance2_subject5', 'fallAndGetUp1_subject5', 'fallAndGetUp3_subject1', 'fight1_subject2', 'fight1_subject3', 'fight1_subject5', 'fightAndSports1_subject1', 'fightAndSports1_subject4', 'jumps1_subject1', 'jumps1_subject2', 'jumps1_subject5', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'sprint1_subject4', 'walk1_subject1', 'walk1_subject2', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk2_subject4', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1'], 'complete_tail_available': True}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。

这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P10。

大产物保留在 /root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/outputs/runs/20261107-p9-critic-full-scale-s0-lafan_h32_survival_critic；用户备份未确认，不自动清理。
