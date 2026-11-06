# P8 指定机制短证据

已完成38089/41379各4条同动作物理展开与C42000四个失败各2个WM窗。

| 更新 | 动作 | 首次真实终止步 | H32根位置误差m | H32仍属有效episode |
|---|---|---:|---:|---|
| 38089 | walk3_subject5 | 25 | 0.316380 | False |
| 38089 | walk3_subject5 | None | 0.253526 | True |
| 38089 | dance2_subject2 | None | 0.222448 | True |
| 38089 | walk3_subject3 | 28 | 0.458588 | False |
| 41379 | walk3_subject1 | None | 0.257342 | True |
| 41379 | walk3_subject5 | 23 | 0.255130 | False |
| 41379 | walk2_subject4 | 31 | 0.421010 | False |
| 41379 | walk2_subject3 | 31 | 0.350282 | False |

| 当前失败动作 | 起点帧 | H32根位置误差m | 预测解析终止概率 | 真实终止 |
|---|---:|---:|---:|---|
| dance1_subject1 | 5293 | 0.075918 | 0.000000 | False |
| dance1_subject1 | 5325 | 0.284063 | 1.000000 | True |
| fallAndGetUp1_subject1 | 6417 | 0.045580 | 0.000000 | False |
| fallAndGetUp1_subject1 | 6449 | 0.160328 | 0.000204 | True |
| fallAndGetUp2_subject3 | 1550 | 0.175236 | 0.000000 | False |
| fallAndGetUp2_subject3 | 1582 | 0.318244 | 0.000000 | True |
| jumps1_subject2 | 10494 | 0.115250 | 0.000010 | False |
| jumps1_subject2 | 10526 | 0.148908 | 0.000487 | True |

比较限于指定初态/context与已存动作；不是闭环策略评分或梯度因果证明。H16/H32判断等待完整正式评分。完整数据与8/16/32步结果见配套NPZ/JSON。
