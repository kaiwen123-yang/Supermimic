# O2 Codex 启动提示词：官方完整BONES首段

本次计划已确定，执行端完成必要适配后直接训练、评分和轻量发布。计划发布不等于服务器已启动。把下面正文交给能够连接autodl-d57的Codex。

```text
请执行 https://github.com/kaiwen123-yang/Supermimic 的O2官方完整BONES首段。用户已在O1完成复核后同意继续推进。先安全同步最新main，保留未提交改动；读取AGENTS.md、docs/O2_OFFICIAL_BONES_PLAN.md、configs/o2_official_bones_protocol.json和docs/O1_REVIEW_20261111.md。直接完成必要薄适配、数据格式转换、正式训练、完整评分和轻量Git发布，不停在再次规划或询问是否开始，不重复上一轮完整审计。

O1已经成功并结束：3h R=.85882311、39/40，final R=.87443989、40/40。其权重/环境/数据保留，不重跑重评O1。当前新主线为O2，P12及独立实现新算法实验继续暂停。O1旧结束约定不阻止本次明确的O2任务。

使用autodl-d57和/root/autodl-tmp/robot-repro/supermimic-official-workspace，复用相邻官方supermimic@abc124c1bd5976341034668af3d12c087f2f1f55、mjlab_research@dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd及supermimic/.venv。不要重新安装/升级，不修改Conda base、其他项目或旧独立实现环境，不停止他人任务。外层代码在用户仓库scripts/o2中实施并部署到工作区work/o2；需要隔离时用明确O2源码工作树，保留原Git/stash。

campaign=20261111-o2-official-bones-s0，run=o2-official-bones-s0，tmux=sm-o2-official-bones-s0。一条单卡、seed0、从零、BONES-only的官方GenCoord/proprio/history10 run。4096真实环境，WM10×2048/horizon8、Actor4096/H32、replay1000/环境、ratio16，保持官方当前main的全部学习路径、normalizer、Muon/Adam、采样、reward/终止/DR。wandb_run_path=None，不载O1或旧独立权重，不混LAFAN配额，不加XYZ/BCE/hard配额/P11高度/P12窗口等修改。

数据直接读取P9保留的BONES manifest及/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9/qpos.npy和qvel.npy。BONES源offset=441140，共47727908帧、130394条；按实际manifest顺序与字段读取，原source_clip_id是BONES clips枚举索引。写工作区data/bones130394_official_packed：保留全部帧和50Hz，按O1关节/坐标映射生成官方六字段、exclusive累计motion_ends、joint_names和motion_names。根局部角速度转world，世界线速度不再旋转。新packed从0起，不带旧offset、不减末帧；训练motion_file传单一packed目录。只需qpos/qvel，不恢复旧NPZ、不重下载/retarget/过滤，不凑论文129514条。原始数组和manifest不改。

训练上限累计12h或官方1000000 collection先到；正式进程导入、全库加载、初始化、编译和必要replay计时，转换/评分/发布另记。约3h、6h和实际final保存固定权重及节点清单。所有save(label)都只保存，不Popen评测，尤其要改O1的final分支；移除O1的.82 stop文件读写，不以.90提前停。完整记录collection、联合学习、WM/Actor/Critic更新与实际时间，不把collection当旧iteration。

训练子进程真正退出后再评分：一个BONES进程只装一次全库，用固定4096-env按长度排序32批（最后3418真实+678 inactive），依次完整评分3h/6h/final；该进程退出后另建40-env LAFAN进程评同三个O2节点。不要每批重建env/重载全库，不实例化完整训练Runner做评测。批量不同起点用计划中的set_time_steps和原生state写入helper；reset_to_frame只接受单个int，不能直接喂起点向量。

保持O1正式口径：frame0、确定性、摩擦1、无DR/噪声、auto_reset=false、只取消训练timeout，保留原奖励和hard阈值；同checkpoint Actor/normalizer冻结。N−1转移为全长，失败尾段在分母，每条R=reward_sum/[.1*(N−1)]，全130394条等权，不能平均各batch均值。所有done行（包括inactive/padding）要完成原生manual reset义务；计分active永久关闭。BONES与LAFAN分别报分，不把跨库LAFAN称为O1遗忘或未经证明的未见泛化。

输出全部逐clip成绩、固定hard639/普通类别/flip/side_roll/cartwheel/handstand分组、节点完成保持与共同完整质量、奖励贡献和XY误差。hard只作分析不影响训练采样。final从同次评分保留计划指定最多8条、每条截至首次硬失败且包含该转移的最多32步小证据；实际k=min(32,本clip已执行转移数)，保存k+1状态/k动作奖励和valid_length=k，不padding、不跨clip/reset取帧、不因短轨迹更换候选，禁止为此额外重放或模型推理。R>.90只称超过SONIC参照，作者单卡25/129514失败另列；成员和硬件差异如实记录，不虚设.91验收线或将LAFAN.82用于BONES。

单Codex交互<=4h，tmux后台跨窗口执行训练和后续评分，不因交接重启活跃replay/LR。训练和评分Torch各2线程，CPU元数据/汇总最多12个单线程worker；评分与发布共用原p2-publication.lock、并发1，训练不持锁。只记录正常运行资源，不加容量benchmark或新learner。已有完整评分分片/发布失败保留并续接未完成部分，不重训重评已完成结果。

保护O1及全部历史原件；O2普通checkpoint沿最近20份滚动规则，保护初始/3h/6h/final和评分引用权重。当前保存不含完整optimizer/replay/sampler/RNG恢复，不把权重加载称full resume；真实错误针对处理并累计已耗预算。禁止新增防御性框架、单元/mock/冒烟/导入/形状/哈希测试、恢复演练、无关扫描或参数搜索。

把实际代码、config、数据索引、全部逐clip CSV分片、紧凑统计、小证据和结论推GitHub；训练节点先推元信息并标评分待执行，评分后推完整成绩。大checkpoint/数组/视频/完整日志留服务器，不Release/tar/本机归档或阶段清理，不介入H盘迁移。及时同步README、AGENTS、results/index和campaign summary，区分计划、已启动、训练结束、评分中、完成。全部实际固定节点的BONES和LAFAN评分及轻量发布结束后交付，不自动加时/seed/变体或开O3。
```
