# P10：两路 8192 环境并行，针对困难技能增加练习

状态：**计划已发布，执行端适配与训练尚未启动**。日期：2026-11-08（北京时间）。
固定依据：P9 已完成提交 `41d26ea07851eb5016fd256a4001aa46bf6711c4`。
复核：[P9_REVIEW_20261108.md](P9_REVIEW_20261108.md)。
执行协议：[next_stage_8k_hard_practice_protocol.json](../configs/next_stage_8k_hard_practice_protocol.json)。
启动提示词：[P10_CODEX_START_PROMPT.md](P10_CODEX_START_PROMPT.md)。

用户本轮明确要求制定并推送下一步，并扩大环境数、充分使用96GB显存与25vCPU。P9“不自动开P10”是旧阶段边界，本次安排由新的明确请求授权。本文件发布不表示训练已经启动。

## 1. 本轮研究问题

P9 已完成正确筛选的130394条BONES、264.43063h完整库训练及正式评分，不能再把“只训练40h、数据尚未修正”当当前状态。完整库训练提高了完整执行数，但姿态质量与困难技能仍有明显缺口。

全库中固定困难集合为 **639条、1.11132h**，仅占约0.49%的clip，却包含终点1174个失败中的459个。P9九千轮给Stunts的真实transition仅115969次、reset895次，359条动作的练习量很有限。增加困难技能的实际训练曝光比继续细分Critic损失变体更直接。

P10的唯一对照变量是困难reset池的固定环境配额。两路共同扩大真实采样、想象和WM学习batch，继续同一个P9完整库父模型的算法与数据。稳定性和规模能力在这两路完整库训练中同步推进；不额外启动LAFAN、H扫描、PPO或新seed任务。

P9 LAFAN上原Critic终点更好，不能据此推断完整库上原Critic也更好。P9完整库存活加权目标实际避开过零存活后缀的大损失；本轮两路均保留现有 `survival_weighted`，不叠加原式切换、zero-mask或其他loss研究。已达到的LAFAN指标验收保留。

## 2. 运行位置、父模型与初始化

campaign：`20261108-p10-8k-hard-practice-s0`。
工作树：`/root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice`。

共同父checkpoint：

`/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/outputs/runs/20261107-p9-critic-full-scale-s0-bones_full_lafan_survival/checkpoint_0009000.pt`

两个独立run/tmux：
- `full8k_control`：原两来源reset配方，扩大batch后继续。
- `full8k_hard_practice`：增加固定hard reset配额。

两路都做**同数据完整resume**，恢复三网络、三套Adam、全部sampler returns/memory、已保存Torch/CUDA RNG、全局迭代9000、Actor计数8995与全局LR。不能改成仅迁移网络、重新初始化Adam、重置cosine或重做5次WM-only。9001开始全部为完整联合更新。

8192环境需要新的物理现场和replay；各填充一次现有64步replay。此后活跃tmux跨窗口持续运行，不能因交接重建replay/LR。真实进程退出后从未存replay的checkpoint恢复，才作必要填充并累计先前已消耗阶段时间；不做恢复演练。

复用主项目现有激活脚本、独立环境、依赖和G1资产，不setup、安装、升级、重建或清理正常环境；保留其他项目及既有工作树、Git/stash。

## 3. 两路共同扩大完整学习批次

| 参数 | P9 | P10两路 |
|---|---:|---:|
| 真实环境 |4096|**8192**|
| 想象batch |4096|**8192**|
| WM每轮batch |10×2048|**10×4096**|
| H / k |32 / 8|保持|
| Critic epochs×minibatches |5×4|保持|
| replay容量 |每环境1000步|保持|
| collect |2/3步交替|保持|
| 两来源环境总额 |1024/3072|**2048/6144**|

每更新平均真实transition为20480；WM窗口40960，Actor起点8192。因此WM窗口/真实transition仍为2，Actor起点/真实transition仍为0.4。不能只把真实环境改大而不配套WM和想象batch，也不把WM optimizer步数从10翻倍。

保留原713根位置反馈/.3m、公共goal710/未来10帧、history930、k8/H32、aux_bce、analytic_smooth温度.05、Actor LR scale=.5、gamma=.99、lambda=.95、奖励、物理终止、PD、动作/观测噪声及随机化。按全局9001..27000接续现有250000余弦日程；不因batch变大自动乘LR。

两路仍依次执行真实采集→WM拟合→Actor/Critic联合更新。存活加权Critic保留当前reward前S_t、固定全rollout分母和首次终止transition；自然终点沿用原clip frame规则，训练500步timeout不新增为想象终止。

两个8192进程合计16384个真实环境，高于P9三路4096的12288；这是两个独立策略的并行研究，不称为一个16384环境策略。

## 4. 困难练习池：只改变抽样入口

### 4.1 冻结639条成员

基于P9已接受的完整BONES清单，取以下并集并按原motion id去重：
- metadata category等于 `Stunts`；
- 原始动作名转小写后包含 `flip`、`side_roll`、`cartwheel`、`handstand` 任一项。

冻结清单记录原BONES source_clip_id、原名称、类别和长度；加载时按现有联合manifest来源字段映射联合库id，不猜偏移、不重新编号。当前实际为639条；来源由P9完整清单确定，不按P10策略分数或失败结果增加、删除成员，也不重新筛选全库。泛BONES池继续包含全部130394条，包括这些hard成员。

### 4.2 source与reset池分开

两个job的 `environment_source_counts` 都为：
- LAFAN：2048；
- BONES：6144。

| reset池 | 控制路 | 困难练习路 |
|---|---:|---:|
| LAFAN全40 |2048|2048|
| BONES完整库 |6144|5120|
| BONES困难并集 |0|1024|

来源仍只有LAFAN/BONES两个；hard是额外reset池，不能伪装成第三source或改变MotionLibrary数据定义。候选路的1024个hard环境每次reset都留在hard池；另外5120个BONES环境照常从完整库抽取，不能把hard从完整池排除。

对任意抽样池B，保持原混合公式：

`p(b|B)=0.5/|B| + 0.4*softmax_B(-25*G_b/10) + 0.1*M_b/sum_B(M)`

所有池使用同一份已恢复的全局per-bin returns G与source memory M；hard历史项是原BONES memory在hard池上的条件分布，不新增独立hard历史EMA，不重置父sampler。

**必要接口：** source group_bins与record()仍只有两个来源；每个来源沿原逻辑每次更新一次memory。不得将第三个重叠hard池放入原EMA循环，否则同一hard bin会重复更新。只让sample()根据固定环境reset池选择候选bins并在池内归一化。

真实环境份额是明确的25% LAFAN、62.5%完整BONES、12.5%专门hard。实际WM k8有效窗口与Actor起点比例按正常采样记录；不能把环境份额当作它们的实测份额。完整BONES池也会抽到hard，因此总hard曝光可能高于12.5%。

## 5. 预算与正式评分

每路新增 **18000次联合更新，9001–27000**，或**累计本新阶段40h**，先到者结束。40h包括正常训练循环与必要replay填充，真实恢复不重置预算；父训练沿革、数据/证据、正式评分和发布分别记录。

若跑满，每路含一次64步填充约369164288个真实transition、4718592000个imagined steps；这是真实扩大后的学习量，不沿用P9的4096 batch成本。保留父完整训练沿革，不称从零、纯BONES或作者3h复现。

### 5.1 使用阶段相对节点

| 内容 | 固定全局节点 |
|---|---|
| 全部130394条BONES正式评分 |15000 /21000 /27000|
| LAFAN40保持评分 |12000 /15000 /18000 /21000 /24000 /27000|
| 真实非整节点终点 |两项都评分；已有相同节点不重复|
| 父9000 |复用已发布同权重结果|

调度必须使用 `iteration-start_iteration`。现有 `iteration % 6000` 在起点9000会排到12000/18000/24000，不能直接沿用。每3000新增轮发布对应紧凑训练统计与已有正式评分，每6000新增轮增加全库评分。

BONES与LAFAN显式选择对应子库，记录联合训练与实际评分定义，普通同数据resume约束保持。BONES全库、冻结hard、其余BONES、20类别、四个名称组、现有40h监测子集以及LAFAN分别报分，不合并成一个总均值。40h统计从同一次完整库结果提取，不另跑子集。

每clip从第0帧，至物理终止或自然末尾；参考N帧，分母0.1×(N−1)，失败剩余部分计零，不用训练500步截短评分。摩擦1、无观测噪声/随机化、同原终止标准。

主要判断是全库和困难组的回报、失败身份、父成功保持、body-orientation贡献及共同完整集合质量，并观察LAFAN保持。困难组提高而普通组下降时同时报告，不能只报成功数；不选最佳单点、不拼接各checkpoint成功并集。固定三个BONES节点全部保留，真实共同节点用于比较。

## 6. 正式评估按参考长度组批

P9完整评分固定1024条混批，必须等组内最长动作结束才换批。已有终点评分标量显示，原顺序需617846个batch控制步；按参考长度排序后为56026，固定槽位计算量/有效步数由13.35降到1.21。它证明存在批次空转，不是新benchmark，也不承诺11倍墙钟加速。

P10正式评分统一：
1. 在评分前按 `(full_reference_steps, original_motion_id)` 稳定排序，每组仍最多1024。
2. 保持所有clip、逐clip初始化与物理/回报语义不变；未完成环境与已完成环境仍按原正确状态处理。
3. 记录 `source_clip_id`，最终标量按原manifest id恢复顺序后分片。两路和所有P10节点使用同样分组协议。
4. 父9000成绩复用，不为排序再跑一次旧父完整评分。

终点失败尾窗仍为flip、side_roll、地面起身/滚动、其余四个既有组，每组原manifest id最小的两个实际失败，共最多8条。排序改变执行顺序后，使用全局每组至多2个候选：更小id的失败替换较大id；不能沿用旧“每批先遇到两个即永久满额”的逻辑。

只在同次正式评估保留现有133帧有界尾窗；批开始仅需捕获仍可能进入对应组前2的clip，候选阈值只会变小。最终一次写出保留的小窗，没有失败的组留空；不保存全库逐帧、不二次回放、不按分数挑尾窗。

## 7. 显存、RAM与并行

P9完整库Torch峰值约19.06GiB/路，8192规模按batch/env线性估计约38.12GiB/路、两路76.24GiB；这不是实际扩大后的测量，仍需给Warp、allocator与正式评分留空间。现有GPU记录为97887MiB。两路扩大训练是本轮目标，不再强塞第三个同规模learner。

- Replay8192×1000约10.963GiB/路；Actor8192×43帧参考窗约339.97MiB。保留replay1000与43帧语义。
- 完整参考继续使用P9的CPU只读mmap。两个job和评分直接引用同一底层绝对目录：`/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9` 中六个.npy。通过已有manifest/reference_store及明确目录链接访问；不复制、重新pack或重新prepare。
- BONES参考约44.98GiB，加LAFAN约.42GiB，由同文件页缓存共享。用户报告120GB RAM有富余；现有P9记录未给出完整主机内存遥测，实际启动时记录已有系统的total/available和正常进程占用，不假造已核验值。
- 顺次完成两个真实训练进程的必要构造/64步填充；首路进入正常联合循环后即启动第二路，避免冷启动峰重叠。不先跑容量试验、不终止首路重来。
- 每训练/评分进程Torch2线程。已有评分分片汇总、短窗读取等CPU工作可用最多12个单线程进程并行；不重复数据处理或新增任务以凑CPU占用。
- 正式评分默认1024批次；按实际共享空间接入。如其他正常项目使空间确实不足，可事先明确改512/256评分批次并记录，两路同用；不能自动重试扫batch或终止其他项目。
- 所有正式GPU评分、下节六个WM证据及Git发布使用唯一已有锁：
  `/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock`。
  总并发1，训练不占锁。评分队列可落后于训练，不能因队列未完自动加训练预算。
- 两路独立run/log/tmux；单Codex交互窗口≤4h，后台可以持续40h。交接不停止正常训练、重建replay或重置LR。

资源记录复用正常日志中的分阶段耗时和Torch峰值，补实际reserved与必要运行节点的GPU占用即可；不部署持续监控服务、不另开吞吐benchmark。训练扩大与已量化的评分空转处理之外，效率专项后置。

## 8. 有限机制证据与正常训练统计

### 8.1 只做六个已确定的同动作WM窗

使用 **P9 full9000当前父WM**，从已经保存的真实失败尾窗起点读取qpos、qvel、previous_action与33维context，逐步喂入该段**实际执行动作**，与同一段真实状态比较。只预测，不运行新物理、不让Actor改动作、不扫额外起点。当前计划发布不执行这些预测，P10实施时一次完成，可与训练并行排队。

| 已有动作 | reference state frame 起→止 | 步数 |
|---|---:|---:|
|flip_180_R_009__A304_M|139→171|32|
|flip_360_004__A304_M|52→84|32|
|side_roll_R_002__A415_M|95→127|32|
|side_roll_R_002__A416_M|78→110|32|
|handstand_ff_start_270_R_001__A305|0→17|17|
|tiger_jump_to_shoulder_roll_R_003__A415_M|94→126|32|

handstand只有17个真实transition，不补帧、不重复末动作扩成32步。按原整数state/action frame对齐，WM从真实起点递归使用自己的预测状态，只固定输入已有实际动作；保存真/预测z、vz、SO3、joint误差、奖励、终止概率及其来源。区分analytic probability与learned BCE head，不将固定动作序列的开环预测称为策略闭环能力。各窗当前父WM只预测一次；不再对旧dance父模型追加预测。dance已有物理成功—失败对照保留报告。

### 8.2 正常计算顺带统计

- 既有Eq2分解、raw/weighted Critic、零S后缀SSE、WM分项、阶段计时保留。
- 真实transition/reset、WM有效窗口、Actor起点分别记录LAFAN/hard BONES/其余BONES的实际数目；hard按clip成员定义，包含完整池抽到的hard。需要区分reset池来源时，复用已采样环境索引，不新增随机采样。
- 每个hard clip累计真实transition、reset、WM窗口、Actor起点，同时记录已访问hard clip/bin数量，显示是否仍有大量成员没有获得有效练习；按规定节点推小型汇总。
- 在已有WM前向的逐样本平方误差/BCE中，按上述三组汇总原分项误差与有效样本数，不新增forward/backward。比较时注明各路replay分布不同；无样本不能伪记零误差。
- 既有剩余参考步分组[1,16]/[17,32]/[33,50]/[51,250]/[251,+∞)继续，来源/困难成员与剩余时长分开。
- 每千轮仍最多4条正常训练selected rollout，沿用raw MSE选样准则。sidecar同时写实际优化objective、raw MSE、weighted MSE、零S后缀/总SSE、S均值、motion/source/hard成员、起点frame与旧V/target参数阶段。不能再只给巨大raw数值而遗漏实际优化目标。
- P10真实终点LAFAN失败窗及上述最多8个BONES失败尾窗均复用正式评分，不额外全动作重放或批量渲染。

## 9. 发布、保留与停止

按节点先推GitHub：代码、实际配置、hard冻结清单、数据与父沿革、全部逐clip评分、紧凑训练/曝光/分组误差统计、六个WM小窗、终点规定尾窗和真实结论。

BONES逐clip标量改为 **每1000条的紧凑CSV分片**，附字段说明、小summary与分片索引；总summary直接给全库/hard/其余、类别与技能组质量、成功身份变化和父保持。原完整结果仍覆盖全部130394条，不为了文件小而省动作。现有40h监测统计从同次全库结果提取。

大checkpoint、完整轨迹/视频、原始与处理数据、大日志留服务器；不Release、不打tar、不在用户电脑归档、不自动阶段清理。训练原有每轮保存、最近20轮滚动及父/整千/最终/续训checkpoint保留规则照旧。必要产物与来源记服务器路径，未经用户确认不标已备份。

禁止防御性编程、单元/mock/冒烟/导入/形状/哈希测试、摘要重算、恢复演练、全盘扫描、无关报告/监控/benchmark；不重装环境、不重做已完成数据准备、不放宽成功标准。遇到真实运行错误才针对修复。

固定预算结束后完成实际终点评分与轻量发布，报告训练/评分/发布三个真实状态。没有达到目标时如实解释，不自动扩预算、更改采样比例、再开Critic/H/PPO/多seed支线或启动P11。

