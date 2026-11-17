# O7 Codex 执行提示词

状态：**单路从零正式训练运行中**。以下保留启动约定；已有活动O7只观察接续，不重复启动。见[执行交接](O7_EXECUTION_HANDOFF.md)。

---

你在autodl-d57继续kaiwen的SuperMimic复现。请实际完成必要适配，然后执行下述已明确的O7；不重复完成的O1–O6，不机械停在“给出计划”。先读仓库当前AGENTS.md、docs/O6_REVIEW_20261117.md、docs/O7_OFFICIAL_NOISE_REMOVAL_PLAN.md和configs/o7_official_noise_removal_protocol.json，按协议推进。旧阶段的“不自动开O7”是旧阶段收尾限制，不覆盖我现在明确调用本提示词执行O7。

## 已确认的依据

O6结果commit为8f23f4b26fc84598dc19429963ddb8cd18cd37ee，完整fresh seed0、parent=null，320000 collection、127997 joint、1310720000真实transition。实际初始化、Adam WD0、CUDA graph可见LR原位更新和结束逻辑均已复核，不需要重做环境或测试。

O6 80k/160k/250k/320k的BONES R分别.922718558/.945902665/.953232182/.953665488，失败164/65/36/39，XY12.738/6.463/5.229/5.180cm。最后70k修复11条、丢失14条；共同完整130344条精度仍改善。hard639失败25→28，monkey_jump18只完成1条；O5Muon曾完成14条。最终39条在O6早期或三个历史参照中都曾完成，不能统称不可行数据。

官方新提交7e94b073940b7a19b9a82ff01e191cfb35c4ba91删除collection Gaussian动作噪声，作者报告Muon/history10、bones_full、300k iterations、2 GPUs在其129514条clean benchmark下2315→1失败，同段另报Adam10→7。作者完整配置及iterations到我方collection/joint的对应未公开，不能称与我方单GPU320k严格同配置。它是论文之后的修正，对我方Adam是否有收益尚待本轮观察。

## O7唯一训练变化

沿用O6完整fresh Adam+cosine，只纳入该官方动作噪声删除。actor输出直接送simulator/replay；删掉额外randn_like表达式，不以noise=0但仍采样随机数替代。保留传感噪声、reset扰动、DR、encoder bias、reward、hard termination、PD、采样器、normalization、goal/state/history和网络结构。

官方源码独立工作树固定7e94b0；研究库固定dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd，继续现有supermimic/.venv/bin/python和现有资产。不得uv sync/install/upgrade/rebuild。新lock不是本轮环境升级授权；旧dd51已用约0.2s bins，别同时改bins或跟新research main。

## 身份与必要适配

- campaign：20261117-o7-official-noise-removal-s0
- run：o7-bones-adam-cosine-noise0-s0
- tmux：sm-o7-adam-noise0-s0
- 用户工作树：/root/autodl-tmp/robot-repro/supermimic-o7-official-noise-removal
- 官方工作区：/root/autodl-tmp/robot-repro/supermimic-official-workspace
- 官方隔离源码：工作区下supermimic-o7-noise0
- 适配器：scripts/o7部署到工作区work/o7

从scripts/o6复用现有薄适配，更新common/driver/run_d57/trainer/evaluator/comparison/publisher所有身份、路径、协议和状态。移植O3统计patch和O5全Adam WD0分支；旧patch在policy.noise处的上下文已经失效，针对7e修正上下文，不能把删除的字段/噪声行补回。官方config loader忽略未知旧字段，有效actual_config要明确collection noise不存在，不留活跃.1的假记录。

保留协议中已提供的fixed_quality_timeseries.members/timing和completion；评分器从前者读六条样本，publisher更新后者及current_execution。同步common.PROTOCOL_PATH、publisher写入路径、计划/提示词/AGENTS/README当前状态和O7 handoff，避免O6旧标签或重复false状态。修订后的实际Adam patch保存到scripts/o7并记入actual_config。新增reset组用O7自己的diagnostics扩展，不改历史scripts/o3，返回原sampler的相同frames。不重复运行旧read_existing_evidence。以上是必要源码适配，不新增测试。

从O6 actual_config取配方，三网络、normalizer、三套Adam、replay、sampler、RNG全部fresh seed0；parent=null、wandb_run_path=None、祖先joint=0。data_lineage直接读现有manifest，不为拿metadata加载父checkpoint。不从O6250k/320k或O5Muon权重续训、蒸馏或拼接。

## 固定训练预算

BONES现有130394条，4096真实环境，GenCoord/proprio/history10。WM10×2048、官方horizon8语义不改；Actor4096/H32，gamma.99/lambda.95，Critic5×4，replay1000/env、ratio16。全Adam WD0；Actor betas(.9,.95)，WM/Critic(.9,.999)，eps1e-8、fused/capturable。

c为本run已完成collection：

lr(c)=2e-4*(.03+.97*.5*(1+cos(pi*min(c,250000)/250000)))

在每次self.step完成后、当前learner前，对三网所有group既有device LR tensor原位fill_；捕获前创建张量，不能只改cfg、替换张量、按WM/critic次数另计或在交接时重置。

320000 collection正常退出是唯一训练预算；无小时截止、无回报早停、无自动加训。节点80k/160k/250k/320k，预期joint31997/63997/99997/127997仅供解释，不能补步凑数。真实transitions预期1310720000，三优化器实际步数如实记录。

这四个是正式里程碑；initial snapshot与普通rolling20保存沿用O6，训练中不评分，完成后只评正式唯一节点。

每次Codex交互≤4小时，tmux跨窗口连续。若任务已活跃，接续观察，不重复启动、不重建replay或LR。真实训练异常如实记状态，保护已有节点；现有checkpoint不包含完整optimizer/replay/sampler/RNG，不能把weights-only恢复写成完整连续run。

## 正式评分与诊断

训练child退出后，沿用O6同一clean evaluator，评全部唯一实际节点：先全BONES，再LAFAN40。复用O6固定结果，不重跑旧checkpoint。

BONES4096环境、32长度排序批次，末批3418有效+678 padding；LAFAN40。首帧参考初态、摩擦1、COM offset0、encoder bias0、无观测/reset噪声，去掉time_out时限，原hard failure不变。每clip分母0.1*(frames-1)，失败步计入、缺失尾部为0，逐clip等权，不把成功前缀均值冒充全时长回报。

每个O7节点与同collection的O6节点配对：全库R/失败/完成率，修复/新增/持续失败身份，共同完整集合R/XY/body orientation与变化分布。另报hard639/nonhard、flip/cartwheel/handstand/side_roll，以及完整monkey18、hook_jump_off_wall12、crutches432、≥60s494条。重点O7自身250k→320k；LAFAN是跨库结果，不撤销O1/P6已达标验收。

同次正式评分只保留六条固定时序：16、63672、101155、124371、1216(monkey_jump_006__A416)、9457(monkey_jump_003__A304)。复用已有QualitySeries，stride5+首步+真实末步/失败，累计reward仍含全部物理步。1216旧O6只有失败短窗、9457主要是标量，不回放补造。终点最多8条32步失败窗，来自原有有界记录器。

正常训练只在已有detached reset_counts中附加monkey_jump/hook_jump_off_wall/crutches三组，复用已选frame/clipID，不新增采样/forward/RNG。准确标记reset share，不说是transition份额或WM覆盖。没有同输入WM预测时，真实参考误差不命名为WM预测偏差。

## 数据边界和并行

现有数据不重筛、不转码、不重pack。已复核原始142220条筛选记录：项目130655→130394，论文129667→129514；不能由净多880推定超集。项目token crutch漏crutches、1167条现库及24个最终失败命中SONIC关键词，是口径线索，SONIC并非SuperMimic确切名单。保留130394正式分母和39失败，不删失败、不凑129514，也不把24个命中扣成15失败。

一路GPU训练，有必要时≤12个单线程CPU worker整理已有身份/过滤诊断与配对表；各GPU进程Torch2线程。正式GPU评分/发布共用原p2-publication.lock、并发1，训练不持锁。共享资源不足就等可用容量，不停其他项目、不增无关试验或容量benchmark。

若作者后来公开真实manifest/config/主成绩checkpoint，只读记录来源和映射，不改活跃run。当前缺失作者工件不是要求反复搜索、下载demo权重或停止本次明确实验的理由。

## 完成与交付

先推实际代码/config、全逐clip评分、紧凑统计、指定小数组和真实结论，同步summary/index/AGENTS/README及O7 handoff的训练、评分、发布状态；论文数据对齐的未解决部分继续标明。评分或发布失败只续该阶段，不重训。

大产物留服务器；不Release/tar、不在用户电脑归档、不自动阶段清理，原rolling20与里程碑保护照旧。保留O6 250k/320k、O5Muon32k和全部验收/研究节点；用户备份未确认不能标已备份。不要改Conda base或其他项目。

禁止单元/mock/冒烟/导入/形状/哈希测试、恢复演练、全盘扫描、通用防御性框架或额外模型/仿真探测；遇到真实运行错误才针对修复。不要同时改Muon、H/k、reset bins、hard配额、reward/终止或合并未获作者接受的PR6/15。

结论按预定节点和固定终点判断。去噪若改善覆盖且保精度，支持本配方收益；若混合或持平，如实报告，与作者Adam影响较小的观察一致，不能自动延长预算或再开一支。固定预算完成即交付，不自动O8，P12继续暂停。

