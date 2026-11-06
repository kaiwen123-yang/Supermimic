# P8 bones40_transfer_h32 实际结果

实际终点 9000，目标 9000。完整成功 16631/17301，全动作回报 0.78952191，完成比例 97.8718%。
本阶段 9000 次训练迭代、8995 次Actor更新，累计本阶段 10.6884h；C42000前序训练 47.1454h 单列。

| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |
|---|---:|---:|---:|---:|
| 0 | 16378/17301 | 0.81325239 | 96.6714% | 0/0 |
| 3000 | 16843/17301 | 0.79646081 | 98.4438% | 16266/16378 |
| 6000 | 16828/17301 | 0.80394229 | 98.3836% | 16260/16378 |
| 9000 | 16631/17301 | 0.78952191 | 97.8718% | 16154/16378 |

尾节点：{'prescribed_iterations': [], 'available_iterations': [], 'mean_return': None, 'available_success_intersection': [], 'complete_tail_available': True}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。

这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P9。

大产物保留在 /root/autodl-tmp/robot-repro/supermimic-p8-stability-scale/outputs/runs/20261106-p8-stability-scale-s0-bones40_transfer_h32；用户备份未确认，不自动清理。

C42000 weights transfer with inherited cost retained; not from scratch or a three-hour reproduction.
