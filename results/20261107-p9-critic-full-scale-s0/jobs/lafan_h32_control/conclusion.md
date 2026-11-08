# P9 lafan_h32_control 实际结果

实际终点 60000，目标 60000。完整成功 38/40，全动作回报 0.89043870，完成比例 98.2337%。
本阶段 9000 次训练迭代、9000 次Actor更新，累计本阶段 12.5396h；H32-51000前序训练 57.8705h 单列。

| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |
|---|---:|---:|---:|---:|
| 52000 | 37/40 | 0.87201869 | 97.3961% | 37/37 |
| 53000 | 38/40 | 0.86443336 | 97.2825% | 36/37 |
| 54000 | 37/40 | 0.88226845 | 98.0631% | 36/37 |
| 55000 | 38/40 | 0.89329453 | 99.4361% | 36/37 |
| 56000 | 31/40 | 0.80458850 | 90.1648% | 29/37 |
| 57000 | 38/40 | 0.89557972 | 99.2401% | 36/37 |
| 58000 | 36/40 | 0.88329185 | 98.4031% | 35/37 |
| 59000 | 39/40 | 0.88441406 | 99.5375% | 37/37 |
| 60000 | 38/40 | 0.89043870 | 98.2337% | 36/37 |

尾节点：{'prescribed_iterations': [58000, 59000, 60000], 'available_iterations': [58000, 59000, 60000], 'mean_return': 0.8860482007069362, 'available_success_intersection': ['dance1_subject2', 'dance1_subject3', 'dance2_subject1', 'dance2_subject2', 'dance2_subject3', 'dance2_subject4', 'dance2_subject5', 'fallAndGetUp1_subject1', 'fallAndGetUp1_subject5', 'fallAndGetUp2_subject2', 'fallAndGetUp3_subject1', 'fight1_subject2', 'fight1_subject3', 'fight1_subject5', 'fightAndSports1_subject1', 'fightAndSports1_subject4', 'jumps1_subject1', 'jumps1_subject5', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'sprint1_subject4', 'walk1_subject1', 'walk1_subject2', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1'], 'complete_tail_available': True}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。

这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P10。

大产物保留在 /root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/outputs/runs/20261107-p9-critic-full-scale-s0-lafan_h32_control；用户备份未确认，不自动清理。
