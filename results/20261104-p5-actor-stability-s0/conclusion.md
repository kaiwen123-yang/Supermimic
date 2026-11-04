# P5 A/B 结果

B在固定终点回报/完整数和末三节点覆盖不低于A，同时成功交集与父动作保持更好；本次预算下建议选B。

| 组别 | 实际终点 | 新联合更新 | 阶段小时 | 完整数 | 回报 | 起身 | 跑步 | 父32保持 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| c0_control | 24000 | 6000 | 6.690 | 34/40 | 0.71313448 | 6/6 | 4/4 | 27/32 |
| actor_half_lr | 24000 | 6000 | 6.809 | 34/40 | 0.75542500 | 3/6 | 4/4 | 30/32 |

## c0_control

六条起身：fallAndGetUp1_subject1：完整，168.20s；fallAndGetUp1_subject4：完整，168.20s；fallAndGetUp1_subject5：完整，168.20s；fallAndGetUp2_subject2：完整，163.90s；fallAndGetUp2_subject3：完整，163.90s；fallAndGetUp3_subject1：完整，102.16s

父成功退化：dance2_subject1, dance2_subject4, fight1_subject2, jumps1_subject5, walk3_subject5

新增成功：fallAndGetUp1_subject1, fallAndGetUp2_subject2, fallAndGetUp2_subject3, fight1_subject5, fightAndSports1_subject1, jumps1_subject2, walk3_subject1

末三共同节点：[22000, 23000, 24000]；回报均值/范围：0.7025300049284355 / [0.6835801733085906, 0.7131344779175189]。

三节点都成功的动作：['dance1_subject2', 'dance1_subject3', 'dance2_subject2', 'dance2_subject3', 'dance2_subject5', 'fallAndGetUp2_subject3', 'fight1_subject3', 'fight1_subject5', 'fightAndSports1_subject4', 'jumps1_subject1', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'sprint1_subject4', 'walk1_subject2', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk2_subject4', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk4_subject1']；其中起身：['fallAndGetUp2_subject3']。

缺失预定节点：[]。

## actor_half_lr

六条起身：fallAndGetUp1_subject1：root_height，117.26s；fallAndGetUp1_subject4：完整，168.20s；fallAndGetUp1_subject5：root_height，63.42s；fallAndGetUp2_subject2：root_height，127.80s；fallAndGetUp2_subject3：完整，163.90s；fallAndGetUp3_subject1：完整，102.16s

父成功退化：dance2_subject1, fallAndGetUp1_subject5

新增成功：fallAndGetUp2_subject3, fight1_subject5, fightAndSports1_subject1, walk3_subject1

末三共同节点：[22000, 23000, 24000]；回报均值/范围：0.7331797184950136 / [0.7039950421874048, 0.7554250030173142]。

三节点都成功的动作：['dance1_subject2', 'dance1_subject3', 'dance2_subject3', 'dance2_subject4', 'dance2_subject5', 'fallAndGetUp2_subject3', 'fallAndGetUp3_subject1', 'fight1_subject3', 'fight1_subject5', 'fightAndSports1_subject1', 'fightAndSports1_subject4', 'jumps1_subject1', 'jumps1_subject5', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'walk1_subject1', 'walk1_subject2', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk2_subject4', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1']；其中起身：['fallAndGetUp2_subject3', 'fallAndGetUp3_subject1']。

缺失预定节点：[]。

## 同集合 XY

共同完整成功集合共26条：dance1_subject2, dance1_subject3, dance2_subject2, dance2_subject3, dance2_subject5, fallAndGetUp1_subject4, fallAndGetUp3_subject1, fight1_subject3, fightAndSports1_subject4, jumps1_subject1, run1_subject2, run1_subject5, run2_subject1, run2_subject4, sprint1_subject2, sprint1_subject4, walk1_subject1, walk1_subject2, walk1_subject5, walk2_subject1, walk2_subject3, walk2_subject4, walk3_subject2, walk3_subject3, walk3_subject4, walk4_subject1

- parent18000（18000）：平均XY误差 2.0585119346013436 m。
- c0_control（24000）：平均XY误差 1.9080687853006215 m。
- actor_half_lr（24000）：平均XY误差 1.9927146916206067 m。

逐动作XY、所有节点评分和动作身份见 comparison.json；区间训练统计与原始产物路径见各arm目录。

P4重点失败片段的观测与解释见 [旧轨迹分析](p4_trajectory_analysis.md)。

这些是40条训练动作的单父版本、单seed结果，末三节点不是独立重复。半Actor学习率的比较不能证明唯一根因。

先阅读退化动作和真实失败窗口，再决定一个具体问题；本次不自动启动新实验。

大权重、逐轮日志、原始评分轨迹和缓存保留服务器，待用户备份；备份未确认，不自动删除。
