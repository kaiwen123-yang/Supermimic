# P11 执行计划：约束世界模型的根高度与垂直速度一致性

状态：**实现与父七窗预测已完成，两路已正式并行训练并完成真实联合更新。** 核实时间：2026-11-10T11:23:31.198241+08:00。实时依据为服务器run日志；[启动快照](../results/20261110-p11-root-height-consistency-s0/summary.json)。
当前证据固定提交：`f0495ea84fbfff2b0b497a6a92a528e2b054546c`。
本文件与 [机器协议](../configs/next_stage_root_height_protocol.json)、[启动提示词](P11_CODEX_START_PROMPT.md)、[P10复核](P10_REVIEW_20261110.md)共同构成下一轮执行定义。用户本次要求分析和发布计划；复制启动提示词到Codex后，按其授权实施和启动。本轮计划不撤销LAFAN既有成功。

## 1. 本轮只回答一个问题

P10困难练习路已使side_roll达到21/22、cartwheel达到85/120，但flip仍0/44、handstand仍0/160。实际困难动作已经进入真实采样、WM和Actor，并非整个困难池被稀释掉。下一轮保持已有完整库和12.5%专门困难环境，在两路8192环境真实并行中，只改变WM下一步root z的计算方式。

假设：当前WM可以分别预测高度与垂直速度，在想象中产生不一致的高度变化；把高度限制为当前与预测下一时刻垂直速度的梯形积分，可能使Actor在更符合真实运动学的模型中学习。是否改善正式控制由本轮结果决定，不能提前宣布为论文遗漏或已找到唯一根因。

### 证据与限度

已有P9父WM同动作handstand窗出现“预测高度比真实高0.23993m，同时预测vz比真实低0.70643m/s”的组合；其梯形残差均值0.02306m/步，真实约0.0002403m/步。该证据属于旧父，不能冒充P10终点WM。

本轮新读到的P10正常selected imagined样本也存在高度—速度不一致，并不限于零存活后缀：
- iteration18846的handstand，S加权平均绝对残差约0.00946m/步；其中S=.981时单步残差−0.01620m。
- iteration20761的cartwheel，S=.9993时残差−0.02704m；另一个cartwheel在S接近1时残差+0.03069m。
- iteration26303的普通动作样本仍有毫米至厘米级单步残差。

这些样本按既有Critic异常选样规则保留，不是总体随机样本，也没有匹配真实未来，不能由此估计全训练发生率或证明当前预测误差的大小。它们支持研究具体模型自由度；本轮启动前补当前父WM的固定同动作证据。

## 2. 固定同父对照与效果锚点

campaign：`20261110-p11-root-height-consistency-s0`。
工作树：`/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency`。

两路共同完整恢复：

`/root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice/outputs/runs/20261108-p10-8k-hard-practice-s0-full8k_hard_practice/checkpoint_0027000.pt`

| 分支 | WM root-z更新 |
|---|---|
| full8k_residual_control | 原独立position residual |
| full8k_velocity_height | 当前vz与预测下一vz的梯形积分 |

两路恢复Actor、WM、Critic、三套Adam、sampler returns/memory、已保存Torch/CUDA RNG、全局iteration27000、Actor计数26995与原LR日程。父已知训练成本 **382024.04194731265秒，约106.1178h** 单列；不称从零或作者3h复现。

保留P10 control27000作为完整库一般质量锚点、P9 LAFAN原Critic60000作为LAFAN效果锚点；不重跑它们。父hard27000已有全库/LAFAN评分复用。两路同父是为了隔离新WM约束，不能把P10 control锚点与候选路差异当成同父单变量结论。

本轮保留hard父的侧滚/侧手翻收益，也必须报告其相对P10 control已经存在的一般动作和LAFAN质量代价。用户已认可的LAFAN复现成功不撤销，不另加验收门槛。

## 3. 唯一前向变化

状态使用现有world坐标qpos/qvel；控制间隔dt=.02秒。

原方式：
`z_next = z + .02 * vz + dp_z`。

候选：
`z_next = z + .02 * .5 * (vz + predicted_vz_next)`。

其中predicted_vz_next必须是**同次WM前向由网络预测的下一垂直速度**，不能取真实next_state、参考速度或额外模型输出。输入/输出都是world z与world vz；不使用body-local z。

先按原公式得到全部predicted velocity；root XY、完整orientation、全部joints与全部velocity维持原公式。候选只替换position中的z，所有后续奖励、解析终止和Actor/Critic路径照常接收该预测状态。

原dp经yaw旋转，z分量不受yaw影响，因此候选等价于把自由dp_z改成.01×dv_z。不要同时改变XY积分、旋转积分、joint积分、state归一化或奖励。

### 继承兼容

保留70维输出head、全部参数名称/形状和Adam状态。原dp_z输出槽保留但不再参与候选z计算；不删除head、不做网络扩列/裁剪、不清空Adam、不重新初始化WM。state loss仍对预测状态70个既有误差坐标计算，z目标仍是真实下一状态高度；候选z误差的梯度通过predicted vz回传。

使用显式配置字段：
- control：`world_root_height_mode: "residual"`；
- candidate：`world_root_height_mode: "velocity_trapezoid"`。

旧checkpoint无此字段时按原独立残差语义读取。这个默认用于明确旧模型含义，不新增通用fallback框架。候选为**完整继承参数/优化器后改变WM前向语义**，不能写成“模型函数完全不变”。

WM的训练与Actor imagination使用同一实例、同一mode。所有同动作证据加载器也必须依据checkpoint config实例化正确mode。真实正式评分只运行Actor与物理，评分规则不变。

梯形公式是20ms间隔的运动学约束，不声称精确复刻MuJoCo四次5ms implicitfast内部更新；接触冲量时真实梯形残差可非零。候选残差近零是构造结果，不能用它作为研究成功标准。

## 4. 两路共同配方

| 项目 | 固定值 |
|---|---|
| 真实环境 / imagination batch |8192 /8192|
| WM |10×4096，k8|
| imagination H |32|
| Critic |5epochs×4minibatches，survival_weighted|
| replay |每环境1000步|
| collect |原2/3步交替|
| 真实来源 |LAFAN2048 /BONES6144|
| reset池 |LAFAN2048 /全BONES5120 /hard BONES1024|
| hard成员 |原冻结639条，all BONES仍包含hard|
| Actor输入/反馈 |713，当前位置误差/.3m，Actor LR scale=.5|
| 参考读取 |原P9同底层CPU只读mmap，43帧窗口|
| LR / gamma / lambda |接续原全局日程；.99 /.95|

保留原奖励、PD、动作与观测噪声、随机化、物理终止、analytic_smooth温度.05、aux_bce、goal/history定义及所有其他训练参数。9000轮内不再调整hard比例、k/H、loss权重、LR或网络容量。

source仍只有两个，reset池仍三个。完整恢复共享returns/memory，hard按原BONES source_clip_id映射；source EMA不因重叠hard重复更新。新阶段统计从零累计，不能把P10曝光当P11新增量；实际同run进程恢复继续累计P11统计与预算。父收集计数461586432、Actor26995和全局LR继续继承；新阶段累计与父沿革分开记录。

不新增WM-only warmup。27001起每轮完整执行真实collect→WM→Actor/Critic。各新进程只作一次必要64步replay填充；物理现场与replay不在父checkpoint中，不宣称逐轨迹精确续接。交互窗口交接不重启进程、不重建replay或LR。

## 5. 固定预算：9000新增联合更新或20h

每路 **27001–36000，9000新增联合更新，或新阶段累计20h，先到即结束**。必要64步填充计入新阶段，父历史、正式评分、指定证据与发布分别记录。实际进程恢复不重新获得20h。

P10同规模正常每轮约6.94秒，9000轮对应约17.36h；20h给共享负载留出有限余量，不是新的性能承诺。9000轮提供三个正式学习节点；6000轮只有两个节点，18000轮在约束效果未明时会直接重复上一轮整段成本。本轮不宣称9000轮足以证明收敛，固定终点与三个节点共同判断。

若跑满，每路预计：
- 新真实transition184844288，含一次64步填充；
- imagined steps2359296000；
- WM prediction steps2949120000；
- Actor计数从26995到35995。

单个Codex交互窗口≤4h，后台独立tmux跨窗口继续。20h上限不是要求训练进程按4h切段。

## 6. 启动前与终点的固定小证据

启动正式训练前，用当前父hard27000的**原WM语义**读取P10困难路正式终点评分已经保存的7条失败尾窗，分别做一次固定同动作递归预测。两路P11实际终点各对**完全同一批输入**再做一次；不在每个中间评分节点重复。

固定源目录：

`results/20261108-p10-8k-hard-practice-s0/jobs/full8k_hard_practice/final_failure_windows/`

| source_clip_id | 固定已有动作 |
|---:|---|
|17|flip_180_R_009__A304_M|
|52|handstand_ff_start_270_R_001__A305|
|93|reach_jump_R_001__A308_M|
|165|flip_360_004__A304_M|
|967|tiger_jump_to_shoulder_roll_R_003__A415_M|
|1877|tiger_jump_to_shoulder_roll_R_001__A304|
|10848|side_roll_R_003__A415_M|

七条都已有完整32步。固定state帧分别为flip180 **143→175**、handstand **5→37**、reach_jump **32→64**、flip360 **55→87**、tiger_R003 **97→129**、tiger_R001 **77→109**、side_roll_R003 **56→88**；action帧到末帧减1。精确来源与整数帧已冻结在 [p11_fixed_real_windows.json](../configs/p11_fixed_real_windows.json)，不按模型误差重新选起点。P10 handstand当前是37步失败，不能照搬旧P9的0→17。

最多7×3=21个rollout、672个预测步，不补帧、不扫窗口、不运行新物理或策略闭环。使用真实起点qpos/qvel/previous_action/context33，此后递归使用模型自己的状态，输入始终是原真实执行action序列，不逐步喂真实状态。

保存并并列报告：
- true/pred z与vz、z-vz离散残差；1/4/8/16/32步误差；
- root SO3、joint误差、原奖励分项；
- analytic终止概率和learned BCE输出，明确来源；
- 固定reference/action整数frame、父/当前checkpoint、mode及数组语义。

主要比较同输入z/vz/SO3/joint误差和实际失败附近的预测，不以候选残差为零代替准确性。七条均为原失败样本，不能将它们当总体分布。即使当前父WM比P9明显改善，也照实报告；不临时扩成大量窗口或借此另开参数扫描。

## 7. 正常训练中顺带补的统计

不增加额外模型/物理forward、backward、随机抽样、梯度扫描或参数复制；只复用当前计算中的张量。

### 高度—速度一致性与实际误差

定义每步
`r_t = z_(t+1) - z_t - .01*(vz_t + vz_(t+1))`。

- WM原k8 forward：记录predicted r和同一已采样真实state/next_state的real r；同时保留现有真实z/vz预测误差，不用r替代预测MSE。
- Actor原H32 imagination：按当前reward前已存在的detach S_t汇总signed r、abs r、r²的S加权均值及分母；保留首次终止transition，不加epsilon或硬存活阈值。自然末尾另记数量，不能把自然末尾裁断与几何失败混为一类。
- 分组仅LAFAN /固定hard BONES /其余BONES，附实际样本数。候选r近零作为实现语义描述，正式收益看真实评分及同输入误差。
- 既有Critic raw/weighted/actual objective、零S后缀SSE和Smean继续；原每千轮最多4条selected rollout规则不变，sidecar补mode与对应r摘要。

### hard各bin实际学习量

在冻结639条、原50帧bin定义下，新增每bin累计**真实transition起点数、WM有效窗口起点数、Actor起点数**。均按原source_clip_id与起点floor(frame/50)归属，WM窗口跨bin仍归其起点。复用已有sample clip/frame；已有reset visited、per-clip四阶段计数保留。对flip/handstand这些bin附同一k8前向的z/vz平方误差与SO(3)平方误差和prediction_samples；从已有误差张量还原物理单位（z为m、vz为m/s、旋转为rad），不新增前向。由起点bin归属全窗口误差，明确这是窗口误差而非该秒每个状态的独立误差。每clip总量和visited-bin数不再被误写成关键相位已经充分训练。

统计用detach后的已有张量在设备端累计，按原千轮块/正式节点集中转CPU，不为日志每步做CPU同步。按既有节点推紧凑bin计数即可；不存每个transition日志、不额外采样补齐bin、不把采样统计变成新的curriculum。本轮hard配额固定，P11中不依据这些计数自动改比例。

## 8. 正式评分与判断

两路均在 **30000 /33000 /36000** 做完整BONES与LAFAN评分。时间先到，在实际终点补两项；已有同checkpoint评分不重复。以iteration−27000排程，父27000已有评分复用。

延续P10：
- 全130394条从frame0至实际失败/自然末尾，分母.1×(N−1)，无训练500步截断；
- 长度与原source id排序组批，默认1024，输出恢复原ID顺序；
- 全BONES、固定hard、其余BONES、20类别、四名称技能、现有40h监测、LAFAN分别报告；
- 四组失败尾窗按原id最小两个从同次正式评分获取，最多8；LAFAN实际失败短窗同次取得；
- 逐clip CSV每1000条，所有失败保留，不另跑监测子集或批量渲染。

主要比较固定36000及全部三个共同节点、父成功身份保持、共同完整集合body-orientation/XY/SO3/joint质量、flip/handstand/side_roll/cartwheel以及LAFAN起身/跑步保持。如果时间先到导致终点不同，分别报各实际终点，并以已有共同正式节点作同更新比较，不为了凑同迭代追加物理评分或训练。成功数和回报同时报告，不挑最佳单点或拼接各checkpoint成功。

若同动作预测改善但正式控制不改善，结论是该约束尚未转化为控制收益；若hard提高而普通/LAFAN回撤，完整报告代价。普通forward误差来自各自演化replay，不能冒充同输入因果比较。没有固定“残差变零即成功”的验收，也不临时延长预算追成绩。

## 9. 实施接口与文件范围

以下是必要适配范围，不新造通用实验框架：

| 现有位置 | 必要变化 |
|---|---|
|supermimic/networks.py: WorldModel|接收明确root-z mode，先计算原predicted velocity，仅候选替换z；保留70head与state_dict布局|
|supermimic/learning.py|构造WM传入cfg mode；在现有k8/H32张量上汇总r及误差，正常三阶段不改|
|supermimic/hard_exposure.py|增加hard每bin的collect/WM/Actor起点计数及指定物理误差；新阶段与真实同run恢复计数语义明确|
|scripts/train.py|接入P11发布入口与阶段27000基点；恢复流程、checkpoint/预算规则沿用已正确P10实现|
|新两份运行config与P11协议|同父、mode唯一差异、9000/20h、三评分节点与七证据输入|
|P11薄启动/评分发布/收尾入口|复用P10排序、CSV、父保持与共同集合函数；删除P10固定9000/27000等任务常量依赖|
|P11小证据入口|加载checkpoint mode，父及两端使用固定七输入；不新增物理或扫描|
|现有summary/资源汇总|完成时用training.json.last刷新latest_training/iteration；附正确阶段状态和必要cgroup字段|

P10正式评分器可以按其已有cfg接口复用，不因阶段名再重写评分算法。现有CSV schema可继续复用。实际修改文件由执行端结合源码确定；不能只改文档而不让训练实例、保存config、证据加载读到同一mode。

## 10. 资源与运行顺序

当前P10两训练各42492MiB，连其他进程约89.11GiB，GPU总95.59GiB；本轮仍两路8k，不再加第三learner或盲升16k。候选新增标量运算几乎不改变显存。每路replay约10.963GiB、参考窗约340MiB。

容器实际RAM上限120GiB，P10启动memory.current约117.70GiB，含可回收页缓存；/proc的宿主大available不代表本容器可用量。沿用同一P9底层只读mmap，不复制约45.4GiB参考、不重prepare。正常启动/发布节点记录cgroup memory.max/current及memory.stat的anon/file/inactive_file，GPU allocated/reserved/进程占用与原阶段计时即可；不另建监控服务。

顺序：
1. 完成必要代码/配置与七条固定输入manifest；使用现有D57环境、依赖、G1资产和数据。
2. 在既有唯一GPU证据/评分/发布锁内完成当前父七窗预测，保存结果。
3. 首路正常构造、恢复、64步fill并进入联合循环，随后立即接第二路；两路独立tmux持续并行。
4. 评分、固定小证据、Git发布沿用唯一锁，总并发1；训练不占该锁。
5. 预算结束完成实际终点正式评分、两端固定证据及轻量发布。

继续每训练/评分Torch2线程；有具体CPU汇总任务时最多12个单线程worker，不为占满25核制造额外工作。正式评分沿用已运行的1024批，不做容量扫梯或自动重试框架，不停止其他项目。

唯一锁继续使用：
`/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`。

## 11. 发布、保护与停止

推GitHub：实际代码/配置、父沿革、全逐clip评分、小summary、正常紧凑训练与曝光统计、指定七窗证据和实际终点失败窗、真实结论。刷新summary的latest_training与最终观察字段，明确训练完成/评分完成/发布完成三个状态。

保留主项目未提交改动、已有工作树/Git/stash、环境、资产、P10control27k和P9LAFAN60k锚点。大checkpoint/完整轨迹/视频/数据/大日志留服务器；原每轮保存、最近20轮滚动和里程碑保护照旧。不Release、不tar、不推后在用户电脑归档，不自动阶段清理或标记用户已备份。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、无关完整性扫描、恢复演练、全盘扫描、容量/吞吐benchmark、无关报告/框架。必要的正式结果汇总按本计划正常执行。禁止setup、安装升级或重建正常环境。真正运行出错才针对修复。

本轮到9000新增联合更新或累计20h停止，完成指定交付；不自动换配额、追加WM-only、扩大预算、开k/H/BCE/LR扫描、多seed、PPO、实机或下一阶段。

