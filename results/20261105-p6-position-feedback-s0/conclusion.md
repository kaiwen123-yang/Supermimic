# P6 当前相对根位置反馈 A/B 结果

B在共同完整集合的XY和全40根位置奖励均优于父模型与A，总体回报/完成及后段保持也支持反馈支；本次预算下建议采用B。

| 组别 | 实际终点 | 新联合更新 | 阶段小时 | 完整数 | 回报 | 起身 | 跑步 | 父成功保持 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_position_feedback | 33000 | 9000 | 9.968 | 36/40 | 0.76340901 | 5/6 | 4/4 | 31/34 |
| root_position_feedback | 33000 | 9000 | 10.087 | 37/40 | 0.86624655 | 5/6 | 4/4 | 34/34 |

## no_position_feedback

六条起身：fallAndGetUp1_subject1：完整，168.20s；fallAndGetUp1_subject4：完整，168.20s；fallAndGetUp1_subject5：完整，168.20s；fallAndGetUp2_subject2：完整，163.90s；fallAndGetUp2_subject3：root_height，142.36s；fallAndGetUp3_subject1：完整，102.16s

四条跑步：run1_subject2：完整，回报0.821914；run1_subject5：完整，回报0.792385；run2_subject1：完整，回报0.800123；run2_subject4：完整，回报0.789564

父成功退化：fallAndGetUp2_subject3, fightAndSports1_subject4, jumps1_subject5

新增成功：dance2_subject1, fallAndGetUp1_subject1, fallAndGetUp1_subject5, fallAndGetUp2_subject2, jumps1_subject2

末三共同节点：[31000, 32000, 33000]；回报均值/范围：0.7617248794715912 / [0.7422590755138313, 0.7795065524367271]。

三节点都成功的动作：['dance1_subject3', 'dance2_subject2', 'dance2_subject3', 'dance2_subject4', 'fallAndGetUp1_subject1', 'fallAndGetUp1_subject4', 'fallAndGetUp3_subject1', 'fight1_subject2', 'fight1_subject3', 'fight1_subject5', 'jumps1_subject1', 'jumps1_subject2', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'walk1_subject1', 'walk1_subject2', 'walk1_subject5', 'walk2_subject1', 'walk2_subject3', 'walk2_subject4', 'walk3_subject2', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1']；其中起身：['fallAndGetUp1_subject1', 'fallAndGetUp1_subject4', 'fallAndGetUp3_subject1']。

缺失预定节点：[]。

## root_position_feedback

六条起身：fallAndGetUp1_subject1：完整，168.20s；fallAndGetUp1_subject4：完整，168.20s；fallAndGetUp1_subject5：完整，168.20s；fallAndGetUp2_subject2：root_height，142.00s；fallAndGetUp2_subject3：完整，163.90s；fallAndGetUp3_subject1：完整，102.16s

四条跑步：run1_subject2：完整，回报0.907308；run1_subject5：完整，回报0.890291；run2_subject1：完整，回报0.888124；run2_subject4：完整，回报0.879885

父成功退化：无

新增成功：dance2_subject1, fallAndGetUp1_subject1, fallAndGetUp1_subject5

末三共同节点：[31000, 32000, 33000]；回报均值/范围：0.8379129879772743 / [0.7911677630082252, 0.8662465543453157]。

三节点都成功的动作：['dance1_subject2', 'dance1_subject3', 'dance2_subject1', 'dance2_subject2', 'dance2_subject3', 'dance2_subject4', 'dance2_subject5', 'fallAndGetUp1_subject1', 'fallAndGetUp1_subject4', 'fallAndGetUp1_subject5', 'fight1_subject3', 'fight1_subject5', 'fightAndSports1_subject4', 'jumps1_subject1', 'run1_subject2', 'run1_subject5', 'run2_subject1', 'run2_subject4', 'sprint1_subject2', 'sprint1_subject4', 'walk1_subject1', 'walk1_subject2', 'walk1_subject5', 'walk2_subject3', 'walk2_subject4', 'walk3_subject1', 'walk3_subject2', 'walk3_subject3', 'walk3_subject4', 'walk3_subject5', 'walk4_subject1']；其中起身：['fallAndGetUp1_subject1', 'fallAndGetUp1_subject4', 'fallAndGetUp1_subject5']。

缺失预定节点：[]。

## 同集合 XY

共同完整成功集合共31条：dance1_subject2, dance1_subject3, dance2_subject2, dance2_subject3, dance2_subject4, dance2_subject5, fallAndGetUp1_subject4, fallAndGetUp3_subject1, fight1_subject2, fight1_subject3, fight1_subject5, fightAndSports1_subject1, jumps1_subject1, run1_subject2, run1_subject5, run2_subject1, run2_subject4, sprint1_subject2, sprint1_subject4, walk1_subject1, walk1_subject2, walk1_subject5, walk2_subject1, walk2_subject3, walk2_subject4, walk3_subject1, walk3_subject2, walk3_subject3, walk3_subject4, walk3_subject5, walk4_subject1

- parent24000（24000）：平均XY误差 2.0013236211192225 m。
- no_position_feedback（33000）：平均XY误差 2.0917192937866336 m。
- root_position_feedback（33000）：平均XY误差 0.06401239119229778 m。

逐动作XY、所有节点评分和动作身份见 comparison.json；区间训练统计与原始产物路径见各arm目录。

最终失败事件来自各arm的failure_windows.json；P5 A24000成功起身轨迹仍保留原服务器位置作为解释参考。

这些是40条训练动作的单父版本、单seed结果，末三节点不是独立重复。位置反馈是本项目假设，不是作者未公开实现；一次超过0.82不等于复现整篇论文。

结合奖励分项和实际失败窗口解释取舍；本次不自动扩预算或启动P7。

大权重、逐轮日志、原始评分轨迹和缓存保留服务器，待用户备份；备份未确认，不自动删除。

## 全40动作奖励贡献与质量缺口

各动作按完整参考时长归一后等权平均；1−R=(1−C)+(C−R)。

| 策略 | 回报R | 完成C | 未执行尾部1−C | 执行段质量C−R |
|---|---:|---:|---:|---:|
| parent24000 | 0.75542500 | 0.96284185 | 0.03715815 | 0.20741685 |
| no_position_feedback | 0.76340901 | 0.96198485 | 0.03801515 | 0.19857584 |
| root_position_feedback | 0.86624655 | 0.99083201 | 0.00916799 | 0.12458545 |

| 策略 | 奖励项 | 实得贡献 | 执行段可得上限 | 执行段缺口 |
|---|---|---:|---:|---:|
| parent24000 | relative_body_position | 0.18226219 | 0.19256837 | 0.01030618 |
| parent24000 | body_orientation | 0.15107670 | 0.19256837 | 0.04149168 |
| parent24000 | body_linear_velocity | 0.17174219 | 0.19256837 | 0.02082618 |
| parent24000 | body_angular_velocity | 0.16346863 | 0.19256837 | 0.02909975 |
| parent24000 | global_root_position | 0.01048376 | 0.09628419 | 0.08580043 |
| parent24000 | global_root_orientation | 0.09042820 | 0.09628419 | 0.00585599 |
| parent24000 | action_difference_penalty | -0.01212393 | 0.00000000 | 0.01212393 |
| parent24000 | soft_joint_limit_penalty | -0.00191272 | 0.00000000 | 0.00191272 |
| no_position_feedback | relative_body_position | 0.18360759 | 0.19239697 | 0.00878938 |
| no_position_feedback | body_orientation | 0.15472446 | 0.19239697 | 0.03767251 |
| no_position_feedback | body_linear_velocity | 0.17341154 | 0.19239697 | 0.01898543 |
| no_position_feedback | body_angular_velocity | 0.16471077 | 0.19239697 | 0.02768620 |
| no_position_feedback | global_root_position | 0.01025368 | 0.09619848 | 0.08594481 |
| no_position_feedback | global_root_orientation | 0.09080496 | 0.09619848 | 0.00539352 |
| no_position_feedback | action_difference_penalty | -0.01233501 | 0.00000000 | 0.01233501 |
| no_position_feedback | soft_joint_limit_penalty | -0.00176897 | 0.00000000 | 0.00176897 |
| root_position_feedback | relative_body_position | 0.18876756 | 0.19816640 | 0.00939884 |
| root_position_feedback | body_orientation | 0.15968023 | 0.19816640 | 0.03848617 |
| root_position_feedback | body_linear_velocity | 0.17924866 | 0.19816640 | 0.01891774 |
| root_position_feedback | body_angular_velocity | 0.16972683 | 0.19816640 | 0.02843957 |
| root_position_feedback | global_root_position | 0.09028940 | 0.09908320 | 0.00879380 |
| root_position_feedback | global_root_orientation | 0.09349191 | 0.09908320 | 0.00559129 |
| root_position_feedback | action_difference_penalty | -0.01250622 | 0.00000000 | 0.01250622 |
| root_position_feedback | soft_joint_limit_penalty | -0.00245182 | 0.00000000 | 0.00245182 |

原始全40评分及逐动作分项保留；不同完成长度的全40分项需结合共同完整集合XY解读。
