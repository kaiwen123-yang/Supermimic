# O6 Codex 启动提示词

状态：**320000次采集训练已完成，待评分**。以下保留启动约定；已有活动O6只观察接续，不重复启动。见[执行交接](O6_EXECUTION_HANDOFF.md)。

```text
继续 kaiwen123-yang/Supermimic 官方复现主线。同步最新main并保留未提交工作，先读：
AGENTS.md
docs/O5_REVIEW_20261116.md
docs/O6_OFFICIAL_ADAM_COSINE_PLAN.md
configs/o6_official_adam_cosine_protocol.json

直接完成O6必要适配、正式训练、既定评分和轻量GitHub发布。O5不重启或扩预算；O1/P6已有LAFAN成功保留，P12暂停。本轮一条fresh Adam+cosine完整训练路径，不追加其它训练臂，不将改善仅归因于cosine，不称已取得论文精确原始run。

一、位置与源码
- campaign=20261116-o6-official-adam-cosine-s0，run=o6-bones-adam-cosine-s0，tmux=sm-o6-adam-cosine-s0。
- 用户树=/root/autodl-tmp/robot-repro/supermimic-o6-official-adam-cosine，适配器scripts/o6。
- 官方工作区=/root/autodl-tmp/robot-repro/supermimic-official-workspace；部署路径统一为work/o6，新隔离官方源码树supermimic-o6-adam-cosine，Python复用supermimic/.venv/bin/python。
- 官方固定abc124c1bd5976341034668af3d12c087f2f1f55，研究库固定dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd。在新树各应用一次O3 detached统计补丁与O5优化器补丁，使用adam_wd0，保留self.o3_diagnostics。launcher/cwd/PYTHONPATH/driver/import来源全部对应O6，不能仍执行work/o5。记录实际source/import/patch。
- 复用现有Python、G1、BONES130394 packed及LAFAN40，不安装/升级/重建，不改旧源码树、Conda base或其它项目。

二、从零与算法配置
- seed0，parent=null，wandb_run_path=None。WM/Actor/Critic、normalizer、optimizer/replay/sampler/RNG全新；不载入任何历史权重/统计。复用O5实际非优化器配置时只读配置字段，data_lineage直接取已有manifest，祖先更新=0，删除parent加载、parent lineage/data_lineage、initial父评分依赖。
- BONES-only130394，4096真实环境，GenCoord/proprio/history10；WM10×2048/horizon8（8存储状态、7监督转移）；Actor4096/H32，Critic5×4，gamma.99/lambda.95、replay_ratio16、joint/collection=.4。沿用官方奖励/终止/DR/sampler/网络/normalizer。不混LAFAN训练，不加hard配额，不改encoder-bias/horizon/表示。
- 三网全部Adam、WD0；Actor betas(.9,.95)，WM/Critic(.9,.999)，初值2e-4，保留fused/capturable与完整参数覆盖。

三、实际LR、计数与退出
- c=本轮已完成self.step()次数。每次采集后c加1，在learner update前执行：
  lr(c)=2e-4*(.03+.97/2*(1+cos(pi*min(c,250000)/250000)))。
  c>=250000后6e-6，c320000结束。
- 遍历world_model_learner.optimizers、policy_learner.actor_optimizers、policy_learner.critic_optimizers的全部param_group。device LR tensor在capture前构造，之后对原对象fill_；不替换tensor、不只改cfg、不按各optimizer.step推进。初始cfg LR与实际group LR分列进入普通日志/节点元数据，无额外probe或测试更新。
- 显式max_iterations=320000，以真实完成collection320000正常退出；不是320000 joint。保留原Ratio/fill，首joint预期c9，终点预期127997 joint、1310720000 real transitions；计数照实，不补跑凑数。
- 正式节点collection80000/160000/250000/320000，预期joint31997/63997/99997/127997；节点只保存，final同物理checkpoint去重。
- 同时修改trainer/common.training_state/publisher/summary/index/handoff的完成逻辑。O5旧逻辑会把collection_iteration_limit标interrupted；O6正常c320000必须标训练完成，评分状态另记。清除32k joint停止、双臂、旧deadline、8/16/32k节点、旧版本/父比较、历史大checkpoint范数读取。
- 无后台小时截止，无回报早停，不自动扩预算。交互窗口≤4h但tmux连续；已有活动O6不重启、不重建replay或LR。真实进程失败保留failed/interrupted与已有节点；checkpoint缺完整optimizer/replay/sampler/RNG，不能weights-only重启拼成连续run。评分/发布失败仅接续该阶段。

四、并行与资源
- GPU只开这一条完整fresh配方；训练/评分Torch和interop各2线程，CPU最多12个单线程worker。不停他人任务，不缩batch，资源不足等待实际资源，不做容量/吞吐benchmark。
- CPU并行只读核对作者原始run配置、筛选成员与项目manifest对应，以及已发布raw中完整但精度回撤的固定动作。未取得原件如实列缺口，不阻断O6；demo checkpoint不得当论文主checkpoint，不删880条凑129514，不按策略失败筛数据。

五、正式评分和证据
- 训练child真实退出后，一个4096-env BONES worker装库一次，长度排序32批顺序评所有实际正式节点；末批3418有效/678 padding inactive，whole-batch inference_mode。之后一个40-env worker评LAFAN。
- GPU评分/发布共用既有supermimic-p6-position-feedback/work/p2-publication.lock，并发1；训练不持锁。异常提前退出只评已有节点并保留中断状态，不伪造缺失终点。
- 沿用R=sum(native reward)/[.1*(N-1)]、失败尾段零、clip宏平均及原生失败条件。发布全逐clip、hard/nonhard、技能与时长组、相邻及固定多节点共同完整集R/XY/body orientation。
- 历史O3 quarter16k/32k、O5 Muon32k和Adam16k/32k分数直接复用，不重放旧模型。O6跨历史成功交集不是父保持或匹配因果对照；LAFAN是BONES-only跨库评分。
- 协议已冻结source_clip_id63672（性能分化）、16（稳定对照）、101155/124371（≥60秒位置回撤），三历史节点均完整。在O6各节点同次既定评分中，仅从已有张量每5步保留机器人/参考anchor XYZ和delta、姿态/位置误差、原生reward/奖励项及已有累计量、参考帧/时间、活跃/终止标志，并含第一个计分转移及末步/失败步。设备端小缓存、批次结束搬CPU，保存小NPZ/schema/env_origin。正式R仍按每步完整累计，不用抽样近似替代；这四条是有意选择的诊断样本，不代表随机分布。不按O6成绩换名单；若失败照实保留，不补跑、不加前向/RNG/批量渲染，不增训练配额。
- final最多8条失败各32步尾窗仍来自同次评分。anchor_pos为z-only；原生termination与post-step/已推进参考质量有时点差，不能靠末帧重判失败。
- 保留已有采集窗口总量、最后joint的WM/value/gradient快照、raw/clamped value/GAE、normalizer、参数范数与实际优化器元数据；总量/快照分清，实际LR与collection/joint/transition计数同记。

六、判断与交付
- 重点判断250k→320k低LR保持段的全库R、覆盖及共同完整质量，并结合早中期节点解释。不只看失败数，不拼逐动作最佳checkpoint；fresh+LR同时改变后改善不能只归因cosine。
- 推送实际代码/patch/配置、全逐clip、紧凑统计/四条时序和真实结论，同步AGENTS/README/index/handoff。部署/运行状态只按实际更新。
- 保护O3/O4/O5既有节点、O2/O1/P6成果和O6固定/final/评分引用节点；普通最近20个滚动规则不变。大checkpoint/完整日志/视频/轨迹留D57，不Release、不tar、不本机归档、不自动阶段清理。
- 不新增单元/mock/冒烟/导入/形状/哈希测试、恢复演练、benchmark、全盘扫描、通用防御框架或其它训练变量。完成有限预算和全部既定评分/发布后交付，不自动开O7。
```
