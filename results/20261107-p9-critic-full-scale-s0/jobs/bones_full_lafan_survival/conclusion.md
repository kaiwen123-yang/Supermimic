# P9 bones_full_lafan_survival 实际结果

实际终点 9000，目标 9000。完整成功 129220/130394，全动作回报 0.84379710，完成比例 99.4491%。
本阶段 9000 次训练迭代、8995 次Actor更新，累计本阶段 13.5329h；H32-51000前序训练 57.8705h 单列。

| 节点 | 完整成功 | 全动作回报 | 完成比例 | 父成功保留 |
|---|---:|---:|---:|---:|
| 0 | 127594/130394 | 0.85934615 | 98.7691% | 0/0 |
| 3000 | 129101/130394 | 0.85001617 | 99.3788% | 127389/127594 |
| 6000 | 129200/130394 | 0.83594072 | 99.4507% | 127335/127594 |
| 9000 | 129220/130394 | 0.84379710 | 99.4491% | 127394/127594 |

尾节点：{'prescribed_iterations': [3000, 6000, 9000], 'available_iterations': [3000, 6000, 9000], 'mean_return': 0.843251328057849, 'complete_tail_available': True, 'available_success_intersection_count': 128558, 'intersection_parts': {'records': 128558, 'chunk_clips': 2000, 'parts': ['tail_success_intersection_0000.jsonl', 'tail_success_intersection_0001.jsonl', 'tail_success_intersection_0002.jsonl', 'tail_success_intersection_0003.jsonl', 'tail_success_intersection_0004.jsonl', 'tail_success_intersection_0005.jsonl', 'tail_success_intersection_0006.jsonl', 'tail_success_intersection_0007.jsonl', 'tail_success_intersection_0008.jsonl', 'tail_success_intersection_0009.jsonl', 'tail_success_intersection_0010.jsonl', 'tail_success_intersection_0011.jsonl', 'tail_success_intersection_0012.jsonl', 'tail_success_intersection_0013.jsonl', 'tail_success_intersection_0014.jsonl', 'tail_success_intersection_0015.jsonl', 'tail_success_intersection_0016.jsonl', 'tail_success_intersection_0017.jsonl', 'tail_success_intersection_0018.jsonl', 'tail_success_intersection_0019.jsonl', 'tail_success_intersection_0020.jsonl', 'tail_success_intersection_0021.jsonl', 'tail_success_intersection_0022.jsonl', 'tail_success_intersection_0023.jsonl', 'tail_success_intersection_0024.jsonl', 'tail_success_intersection_0025.jsonl', 'tail_success_intersection_0026.jsonl', 'tail_success_intersection_0027.jsonl', 'tail_success_intersection_0028.jsonl', 'tail_success_intersection_0029.jsonl', 'tail_success_intersection_0030.jsonl', 'tail_success_intersection_0031.jsonl', 'tail_success_intersection_0032.jsonl', 'tail_success_intersection_0033.jsonl', 'tail_success_intersection_0034.jsonl', 'tail_success_intersection_0035.jsonl', 'tail_success_intersection_0036.jsonl', 'tail_success_intersection_0037.jsonl', 'tail_success_intersection_0038.jsonl', 'tail_success_intersection_0039.jsonl', 'tail_success_intersection_0040.jsonl', 'tail_success_intersection_0041.jsonl', 'tail_success_intersection_0042.jsonl', 'tail_success_intersection_0043.jsonl', 'tail_success_intersection_0044.jsonl', 'tail_success_intersection_0045.jsonl', 'tail_success_intersection_0046.jsonl', 'tail_success_intersection_0047.jsonl', 'tail_success_intersection_0048.jsonl', 'tail_success_intersection_0049.jsonl', 'tail_success_intersection_0050.jsonl', 'tail_success_intersection_0051.jsonl', 'tail_success_intersection_0052.jsonl', 'tail_success_intersection_0053.jsonl', 'tail_success_intersection_0054.jsonl', 'tail_success_intersection_0055.jsonl', 'tail_success_intersection_0056.jsonl', 'tail_success_intersection_0057.jsonl', 'tail_success_intersection_0058.jsonl', 'tail_success_intersection_0059.jsonl', 'tail_success_intersection_0060.jsonl', 'tail_success_intersection_0061.jsonl', 'tail_success_intersection_0062.jsonl', 'tail_success_intersection_0063.jsonl', 'tail_success_intersection_0064.jsonl']}}。全部动作、起身/跑步身份、父失败演变及1−R=(1−C)+(C−R)见逐节点comparison.json；八项奖励积分在evaluation.json。

这是固定预算结果；不挑最高节点、不合并各节点成功动作、不自动延长或启动P10。

大产物保留在 /root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/outputs/runs/20261107-p9-critic-full-scale-s0-bones_full_lafan_survival；用户备份未确认，不自动清理。

H32-51000 weights transfer with inherited cost retained; not from scratch or a three-hour reproduction.
LAFAN单独保持评分：29/40、R=0.69701160。

| 固定名称组 | 条数 | 完整成功 | 全时长回报 | SO3 rad |
|---|---:|---:|---:|---:|
| flip | 44 | 0 | 0.29520172 | 0.114374 |
| side_roll | 22 | 3 | 0.24389930 | 0.494130 |
| cartwheel | 120 | 8 | 0.31128571 | 0.203025 |
| handstand | 160 | 0 | 0.03482433 | 0.111572 |

全库/类别/固定40h监测与八项奖励分解在quality；全部逐clip及成功身份变化以2000条分片保存。主结果不由最高节点或总体成功率替代困难技能质量。
