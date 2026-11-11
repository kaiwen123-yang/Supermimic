# O1：作者公开研究库后的正式接入

2026-11-11，本轮后续检索找到了作者正式发布的[HybridRobotics/mjlab_research](https://github.com/HybridRobotics/mjlab_research)。原kevinzakka地址仍404，但已不构成源码获取阻塞。当前执行状态以[O1结果目录](../results/20261111-o1-official-lafan40-s0/)中的summary.json和D57现场progress.json为准；此前13:42的readiness.json是依赖尚未公开时的历史快照。

## 版本与依赖

| 项目 | 本轮固定版本 |
|---|---|
| SuperMimic | abc124c1bd5976341034668af3d12c087f2f1f55 |
| 研究版mjlab | dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd |
| 实验标签 | 官方当前main GenCoord/proprio/history10，seed0，完整LAFAN40 |

SuperMimic main发生了提交替换。相对先前5efbf114，只有README、包描述和CI依赖地址改变，学习源码没有改变。README明确将研究库地址改为HybridRobotics/mjlab_research；研究库公开提交提供多动作loader、FK、external采样和reset_to_frame，来源证据见[source_resolution.json](../results/20261111-o1-official-lafan40-s0/source_resolution.json)。

新研究库为mjlab1.6.0，要求Torch>=2.14、MuJoCo/mujoco-warp3.16系列、Warp>=1.15和rsl-rl-lib5.5.2。SuperMimic旧锁仍记录研究库1.5.0，因此在本轮独立Python3.13环境中按新公开依赖要求重新解析并保存实际锁。核心运行版本进一步依作者研究库uv.lock固定为Torch2.14.0、Warp1.18.0、MuJoCo/mujoco-warp3.16.0，rsl-rl-lib为5.5.2；相关约束只写入O1工作区的pyproject，不修改旧环境。本轮使用作者当前发布组合，不声称论文历史run config已经取得。

工作区仍为`/root/autodl-tmp/robot-repro/supermimic-official-workspace`；源码为相邻`supermimic/`和`mjlab_research/`，新环境位于`supermimic/.venv`。uv、Python解释器、安装缓存和训练编译缓存都位于这个工作区内。原项目环境和其他任务保留。

## 数据接入

40条动作由原`data/lafan40_existing50hz`引用读取，转换输出为`data/lafan40_official_npz`。每条保留所有原帧，输出研究MotionLoader实际要求的root_pos_w、root_quat_w（wxyz）、root_lin_vel_w、root_ang_vel_w、joint_pos、joint_vel、joint_names；关节按研究版G1 XML顺序映射，原根坐标角速度旋转到世界坐标。没有重新插值、retarget、裁剪动作或修改原件。

训练和评分都显式使用转换manifest中的同一有序40条路径。转换来源和逐条映射见[official_data_manifest.json](../results/20261111-o1-official-lafan40-s0/official_data_manifest.json)，转换代码为[scripts/o1/convert_lafan.py](../scripts/o1/convert_lafan.py)。BONES索引与现有大缓存保持原状，本轮不启动BONES。

## 运行、评分与保存

唯一正式训练会话名为`sm-o1-official-lafan40-s0`，入口[scripts/o1/run_d57.sh](../scripts/o1/run_d57.sh)。网络和学习更新调用所选官方实现；外层适配只负责数据/config、计数、墙钟预算、本地保存和评测发布。4096真实环境、WM10×2048/horizon8、Actor4096/H32、return sampler、官方normalizer和Muon/Adam等机制保持。

训练初始化、编译及必要replay积累计入累计12h；此前环境安装和数据转换单列。约3h/6h和实际终点保存固定节点并启动全40评分。12h或原迭代上限先到结束；任一正式节点R>=.82时，评分进程写入达标通知，训练进程在正常循环边界保存实际终点并结束。初始化真实失败后的已耗时间通过明确的previous-training-seconds累计，不重新获得预算。

每个节点评分和发布共用既有p2-publication.lock；训练不持锁。评分采用研究版真实环境、同checkpoint的Actor和normalizer，每条从frame0开始，确定性动作、摩擦1、COM偏置0、encoder偏置0、无观测噪声；保留原奖励和硬失败阈值，只取消训练timeout。全部原参考N−1个转移为分母，即0.1×(N−1)，总分为40条归一化回报的算术平均。失败动作保留。跟踪质量按执行前缀和跨节点共同完整集合报告。

官方环境原有reward/termination计算时序保持；终止状态由auto_reset=False保留，已结束的环境在继续批处理前显式重置，其后样本不再计入该clip。原足摩擦、COM和encoder事件保留相同context列，但评测取固定值；加载checkpoint的context统计，避免改变WM输入维数。

权重存于`outputs/o1-official-lafan40-s0/checkpoints/`，日志为同目录`train.log`，实时状态为`progress.json`。保存三网络和normalizer及实际config/计数；没有完整optimizer/replay恢复入口，不将这些文件称为完整resume。W&B只写本地offline日志，未接入模型上传或artifact删除。现有进程跨会话保持运行。

节点worker通过已认证gh Git Data API发布完整轻量评分、config、统计和结果索引，不上传权重或完整日志。Git发布失败保留已算分数，后续节点一并发布已有结果，不重训重评。最终状态与发布commit分别保留在run目录的publication_*.json中。

本轮不执行单元/mock/冒烟/导入/形状/哈希测试、恢复演练或benchmark。只以真实环境安装、数据转换、正式训练及既定完整评分推进。P12和其他独立实现新实验继续暂缓，已有LAFAN1成功结论保持。
