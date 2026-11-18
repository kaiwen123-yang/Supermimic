# SuperMimic 最终迁出 AutoDL 并归档到 H 盘

日期：2026-11-18（北京时间）。目标仓库：`kaiwen123-yang/Supermimic`。本文件是可交给本机执行端的最终迁出任务，**不是迁出完成记录**。

## 1. 当前结论、授权与访问边界

用户本轮明确要求：检查最后一轮是否完成；完成后，把 AutoDL 上所有 SuperMimic 内容（包括系统盘中的项目内容）迁至 `H:\Supermimic`，确认归档后移除服务器原件，不影响其他环境。此授权覆盖此前“源码、环境、模型继续留服务器”“不归档、不清理”的阶段默认约束，无需再次询问是否开始或是否删除已确认归档的项目专属原件。

已读取的结果版本为 [d36b5b54dd6cf8af5733919f273bd6700a9518c3](https://github.com/kaiwen123-yang/Supermimic/commit/d36b5b54dd6cf8af5733919f273bd6700a9518c3)。O7 的训练、正式评分与轻量发布均已完成，复现阶段按用户既有决定关闭；不启动 O8、P12、补种子或任何新复现实验。

**本次会话没有挂载用户 Windows 的 H 盘，也没有可用的 D57 SSH 连接。当前只完成仓库与历史记录核查，新增传输 0 字节、服务器删除 0 项；H 盘现状、可用空间、服务器现存量与活动进程均未现场确认。** 迁出任务状态为 `planned_access_blocked`。执行端必须是能够同时读取真实 `H:\Supermimic` 和通过既有 SSH 配置连接 `autodl-d57` 的本机 Windows/WSL 环境。不得把聊天容器里的同名目录当成 H 盘，也不在聊天或 GitHub 中索取、输出 SSH 私钥或访问令牌。

## 2. 最后一轮结束的依据

| 项目 | 已发布记录 |
|---|---|
| Campaign | `20261117-o7-official-noise-removal-s0` |
| 总状态 | `completed` |
| 训练、正式评分、轻量发布 | `training_done=true`、`formal_evaluation_done=true`、`lightweight_results_published=true` |
| 实际终点 | 320000/320000 collection，127997 joint，1310720000 real transitions |
| 训练退出 | 2026-11-17 22:17:40.810521 +08:00，子进程退出码 0 |
| BONES 评分结束 | 2026-11-17 23:12:22.771996 +08:00 |
| LAFAN 评分结束 | 2026-11-17 23:25:45.233719 +08:00 |
| 结果汇总更新时间 | 2026-11-17 23:25:48.532916 +08:00 |
| GitHub 结果提交 | 2026-11-17 23:25:59 +08:00，`d36b5b5` |
| 大产物本地备份 | 历史 summary 仍为 `backup_status=not_confirmed_by_user`；不能用轻量发布代替本地归档 |

四个实际训练节点 80k/160k/250k/320k 均已有正式评分。终点 BONES 回报 0.9533110456，130375/130394 完整、19 失败、平均 XY 0.05197285 m；monkey 18/18。覆盖改善不代表所有精度指标全面优于 O6。本迁出任务复用已经发布的结论，不为归档重跑训练、模型评分或诊断。

依据：[summary.json](../results/20261117-o7-official-noise-removal-s0/summary.json)、[training_child_exit.json](../results/20261117-o7-official-noise-removal-s0/training_child_exit.json)、[bones_full_worker.json](../results/20261117-o7-official-noise-removal-s0/bones_full_worker.json)、[lafan40_cross_library_worker.json](../results/20261117-o7-official-noise-removal-s0/lafan40_cross_library_worker.json)、[执行交接](O7_EXECUTION_HANDOFF.md)。其中 training_endpoint/latest_training 的 pending 字段是历史退出快照，应结合较新的 worker 和 summary 判断。

上表证明已上传的 O7 完成状态。**删除前仍需现场确认没有后续训练、评分、发布或其他项目进程使用待迁出路径。** 若出现真实活动任务或新状态冲突，保留现场并报告，不杀进程、不重启或补跑实验，也不把“GitHub completed”当成当前进程已退出的替代证明。

## 3. 先读现有 H 盘结构，保留历史归档

历史原件确认 2026-11-11 已执行会话 `20261111_1144`：278/278 批、436114 个源文件；归档完整读取量 374450935401 bytes，覆盖源逻辑大小 379710421814 bytes。当次删除源逻辑大小 188259758855 bytes，保留 191450662959 bytes。随后 NPZ 专项清理又完整读取 66 个 H 包、99538984960 bytes，并删除了获授权的历史 NPZ；当时原保留集合剩余 92489194148 bytes。**这些全部是历史数值，不是今天的 H 空间或服务器剩余量。**

依据：[导出说明](../results/storage_export/20261111/README.md)、[逐批回执](../results/storage_export/20261111/status.json)、[后续 NPZ 清理说明](../results/storage_export/20261111/npz_cleanup/README.md)、[后续清理原件](../results/storage_export/20261111/npz_cleanup/result.json)。硬链接曾造成逻辑删除量与实际释放空间显著不同，本次也必须分别报告。

历史目录结构如下，执行端先读取实际目录，不直接运行初始化脚本覆盖或重建：

```text
H:\Supermimic\00_inventory\20261111_1144
H:\Supermimic\01_source_datasets\BONES
H:\Supermimic\01_source_datasets\LAFAN1
H:\Supermimic\02_processed_data\active_copy_only
H:\Supermimic\02_processed_data\retired
H:\Supermimic\03_checkpoints\anchors_copy_only
H:\Supermimic\03_checkpoints\historical
H:\Supermimic\04_trajectories
H:\Supermimic\05_logs
H:\Supermimic\06_videos
H:\Supermimic\07_results_and_configs
H:\Supermimic\98_incoming
```

已有 `copy_only` 目录名是历史语义，不要求重命名，也不继续强制服务器保留；新的来源、迁出与删除状态写入新会话清单。保留旧包、旧索引与旧回执，不覆盖、合并改写或删除它们。

首先读取 H 盘真实根路径、文件系统、容量与可用空间，顶层及下一层目录，`00_inventory` 各会话和 `98_incoming` 未完成文件。可使用只读辅助脚本 [inspect_supermimic_archive.ps1](../scripts/inspect_supermimic_archive.ps1)，它不创建目录、不传输、不删除，也不替代逐包检查。本会话没有运行 Windows 脚本。

若现场没有同类目录，可新增 `08_source_and_git`、`09_environments_and_assets`、`10_system_disk_residuals`，保持现有“分类/阶段或工作树/批次”的结构。新会话使用实际开始时刻生成的唯一编号；文件名不得复用 `20261111_1144`。

## 4. 迁出范围：项目专属全部纳入，共享原件保护

### 4.1 数据盘与代码工作区

以现场目录和真实引用为准，已知根在 `/root/autodl-tmp/robot-repro/`：

- 主项目 `supermimic`，仍存在的 P 阶段与 O 阶段工作树，`supermimic-publications`，项目 `.cache/execution-worktrees` 和 `.cache/publication-worktrees`。
- `supermimic-official-workspace` 全部项目专属内容：官方源码、`mjlab_research`、隔离训练源码、`.venv`、`.python`、`.uv-cache`、`tools`、`.cache`、data、outputs、results、work 等。O7 当前解释器引用为 `supermimic-official-workspace/supermimic/.venv/bin/python`。
- `supermimic-o7-official-noise-removal`、官方工作区内 `supermimic-o7-noise0`，以及现场发现的其他专属根；名称只用于发现候选，不能代替归属确认。
- 所有仍存的原始数据、处理数据、memmap/packed 数据、数据清单、normalizer、checkpoint、replay、轨迹、逐动作评分、NPZ 小证据、日志、视频、配置、下载中间件与项目临时文件。曾受保护的 P6/O1 验收模型、O6 250k/320k、O5 Muon32k 和各历史节点均归档，确认后可删除其服务器专属副本。
- 源码和 Git 原件：已提交、未提交、未追踪、忽略文件、完整 Git common-dir、对象、refs、stash、reflog、LFS 与工作树管理元数据。不能只打包工作树的 `.git` 指针文件，也不能用 GitHub main 或一个 git bundle 代替所有本地状态。保留各工作树与 common-dir 的映射；common-dir 在其依赖和本地记录都归档后最后处理。

先从实际 `git worktree list`、`git rev-parse --git-common-dir`、运行配置、`pyvenv.cfg`、解释器链接、editable install/`.pth` 与数据链接解析外部依赖。对 Git 的读取不执行 reset、clean、gc、prune 或迁移前的 worktree remove。待迁出的每个工作树目录必须保存实际文件状态。

来源：[O1 启动脚本](../scripts/o1/run_d57.sh)、[O7 交接](O7_EXECUTION_HANDOFF.md)、[历史导出范围](STORAGE_EXPORT_TO_H_20261111.md)。旧导出脚本跳过 `.git/.venv/.cache`，旧 ROOT_NAMES 和固定会话也未覆盖后续官方阶段，不能原样运行后宣称完整迁出；更早的 GitHub Release/hash/恢复脚本同样不是本次入口。

### 4.2 系统盘

系统盘范围是**属于 SuperMimic 的内容**，不是整台机器的系统镜像。检查真实挂载点，避免把 `/root/autodl-tmp` 目录名当成唯一磁盘归属依据。

- 明确候选 `/root/.config/supermimic/`；源码曾引用其中的 `hf_token`。只在本机受限权限位置保存确需保留的项目凭据原件，公开清单只记录路径和处理状态，不输出内容，不上传 GitHub。若实际无法安全保管，单独保留并报告该项阻塞，不影响其他可完成批次。
- 从实际启动参数、环境配置与文件引用查找项目专属 Conda/venv、外部解释器、模型/资源下载、日志、wandb、编译缓存，以及 `/tmp`、`/var/tmp`、`/dev/shm` 中的专属临时文件。只核查元数据和必要的项目内容，不导出全局环境变量或无关日志。
- `/root/.cache/warp`、`.cache/torch`、`.cache/torch_extensions`、`.triton/cache`、`.nv/ComputeCache`、`/tmp/torchinductor_root` 只是候选，不能假定存在或独占。官方启动已把多种缓存重定向到工作区，应先以实际配置为准。对共享目录只处理已证明归属的子项。
- 若存在指向项目的 shell 初始化、定时任务、服务或 root 下符号链接，仅处理确属 SuperMimic 的条目，并保存修改前相关原件；不得重写其他项目的配置或清空全局历史。仍活动的条目须先查明用途，不能盲目停止。

源码依据：[fetch_bones_p8.py](../scripts/fetch_bones_p8.py)。本次核查没有读取任何 token 内容。

### 4.3 共享依赖与其他项目

以下已有共享或外部依赖证据，不能因为 SuperMimic 用过就整目录删除：

| 路径/内容 | 处理原则 |
|---|---|
| `/root/autodl-tmp/tools/python/cpython-3.11-linux-x86_64-gnu` | 旧 venv 的基础解释器；核实其他引用，必要时归档依赖副本，不能默认删除共享安装 |
| `/root/autodl-tmp/tools/uv-env`、`/root/autodl-tmp/robot-repro/.cache/uv` | 共享工具与缓存；区分可独立保存的项目子项和共享原件 |
| `/root/miniconda3` 根、Conda base、共享 pkgs、系统 Python、CUDA/驱动/系统库 | 不整删、不改动；迁移工具使用它们不构成项目所有权。`envs` 下经核实确为 SuperMimic 独占、无其他使用者的环境子目录仍应归档迁出 |
| 全局 HF token、`.ssh`、gh 认证、全局 Git/代理配置 | 不是本项目清理对象，不整包归档到项目公开材料 |
| MPC-RL/MCP-RL、π0、π0.5、pi-reproduction 等目录和进程 | 不修改、不停止、不重装，不更换它们的解释器或依赖路径 |

依据：[历史 pyvenv.cfg](../results/storage_cleanup/20261101/pyvenv.cfg)、[activate.sh](../scripts/activate.sh)。

“归档一份必要依赖”与“删除服务器共享安装”分别决策。若其他项目仍依赖某个名为 SuperMimic 的路径，不能为了名称清零破坏它或擅自改造其他项目；保留该项、记录明确依赖与原因，并把完整迁出标为未完成。只有项目专属源项均已迁出，且残留中没有未解决的项目文件，才可报告项目迁出完成。通用共享系统依赖本身不算 SuperMimic 专属残留。

## 5. 本机执行顺序

### A. 确认就绪并冻结清单

1. 读取本文件、提示词、最新 AGENTS 与 O7 完成原件；检查最新仓库提交，保留本机已有未提交工作，不使用 reset/clean。
2. 验证真实 H 盘与既有 `autodl-d57` 通道。缺任一通道则准确报告，不能在替代目录伪造本地副本，不能绕过凭据或访问控制。
3. 现场核对 O7 与发布任务已退出，检查待迁出路径的活动进程、tmux、锁及其他项目引用。只记录必要的相关命令和路径，避免把无关进程参数或凭据写入日志。
4. 读取 H 盘既有结构和回执；在源盘可用空间、H 空间、文件系统单文件限制与当前其他任务负载确定后，建立新会话。容量不足则完成能够独立验证的批次后准确报告，不删除未确认项目、不格式化盘、不占满系统盘。
5. 对每个源项记录绝对路径、realpath、类型、链接目标、设备/inode、大小、mtime_ns、权限/所有者、预定归档位置、项目独占或共享的依据。清单含隐藏文件、空目录与 Git common-dir。冻结后发现新增或变化文件，必须作为新的待归档项处理。

迁移控制器与日志放在本机，并使用服务器独立的少量会话临时目录；不能把唯一控制器、日志或收据放在即将删除的项目环境里。使用现有工具，不安装、升级或重建环境，不动 Conda base。

### B. 分批归档到 H

1. 沿用实际分类结构，创建独立新会话索引与批次；不覆盖历史包。每个源路径必须能查到包路径和成员名。
2. 用能保留 Linux 路径、权限、可执行位、符号链接与硬链接语义的归档容器保存源码和环境。不要把 Linux 工作区直接平铺成 Windows 文件树。遇到特殊文件类型需明确记录并采用支持的保存方式，不静默跳过后删除。
3. 记录所有符号链接真实目标和依赖是否已在本地保存；不盲目跟随链接把其他项目整包带走。跨包硬链接必须有完整可取回的目标内容和映射；不能产生指向缺失成员的包。必要时跨包保存独立文件副本。
4. 已压缩数据或已有完整包可直接转移或用不重复压缩的 tar 分批。建议从约 2–4 GiB 的可独立验证批次开始，按实际空间和文件系统限制调整；FAT32 下每个物理文件必须低于 4 GiB，超大源文件采用有顺序清单的分片，并在本地完整重组流检查后才能删除原件。不格式化 H 盘。
5. 不在服务器先生成整个项目的第二份巨型副本。采用有界临时空间，批次验证后及时删除该批临时包。先从 1–2 路低优先级打包/传输开始，依据其他任务实际负载调整；不照搬历史 8 路配置，不使用 GPU 或做吞吐基准。
6. 旧 H 包只在完整读取成功、成员与源清单可对上，并将待删除的当前源文件与对应本地解码成员作流式逐字节比较一致时复用；删除前还要核实源身份和元数据未变。名称、日期、历史 completed 字段、压缩包存在或 mtime 相同都不够。无法确认时新建增量包，保留旧包。对早已删除服务器原件的历史包，不伪称本次完成了源内容比对，也不因此覆盖或清除历史包。

环境原件和版本记录用于保存研究现场；不承诺原 Linux venv 可在 Windows 直接运行，也不进行恢复演练、环境重建或 import/smoke/shape/unit/hash/性能测试。

### C. 逐批确认，再删除对应专属源项

一批进入可删除状态，必须同时满足：

- 传输已结束，无 `.partial` 或未关闭写入；本地包与传输源包/流的记录字节数一致。
- 使用对应解码器完整读取本地归档数据和各普通成员内容，返回成功；仅列出目录或执行 `tar -t` 不算。分片必须按清单顺序读完整重组流。
- **内容确认必须有依据：**新生成的归档若实际启用了覆盖文件数据的内建校验，本地完整解码时须确认该校验成功；不能只按扩展名推定。普通未压缩 tar、其他无数据校验的直接复制文件，必须将本地解码成员/文件与当前源内容作流式逐字节比较一致后才可删除。旧包复用同样按上一节逐字节确认对应当前源内容。使用现有工具，不新增 hash 脚本；这些属于必要的传输内容确认。
- 包内成员、源文件集合、大小和可保存的元数据与冻结清单相符；符号链接与硬链接的目标内容可在明确映射中找到。直接复制的原有包也须完整读其内容。
- 删除前再次核实源路径类型、设备/inode、大小、mtime_ns 和依赖归属未变，无新写入者。变化或归属不清的文件留在服务器并记录。
- 本地完整读取与源检查的回执已在 H 的本会话清单中持久化；本地包此后不得被覆盖或修改。

普通 tar 的 `chksum` 覆盖头部，完整读过文件内容、大小相同并不单独证明内容一致；zstd 等格式的数据校验也需要实际启用并检查成功。依据：[GNU tar 格式说明](https://www.gnu.org/software/tar/manual/html_node/Standard.html)、[zstd 官方命令说明](https://github.com/facebook/zstd/blob/dev/programs/zstd.1.md)。

这些是传输和归档确认，不是模型测试，也不产生未执行的哈希等值或“已验证可恢复运行”的结论。不得用哈希脚本或只核对文件数替代以上流程。内建归档校验与必要的直接内容比较不需要新增模型测试、测试框架或恢复演练。

删除仅限**这一批已确认且可独占删除的精确源路径**。不得使用全目录通配删除、全盘 find-delete、`rsync --remove-source-files`、tar remove-files 或以目录名匹配的 `rm -rf supermimic*`。先按清单移除原件，再删除确认为空的专属目录。每个顶层根清空前重新核对新增文件；Git common-dir、仍在用的工具和迁移收据最后处理。对其他项目共享的链接/依赖保留原件并记录。

若断线、读包失败、空间不足、源文件变化或归属有疑问，保留未确认的源文件和既有完整包，记录具体批次；可以继续无依赖的安全批次。不要重新下载已验证且未变化的包，也不要把失败包标记为完成。

### D. 最终复查和交付

1. 对清单内项目根、外部目标及已发现的系统盘位置再做项目范围的只读残留核对，检查项目进程、锁、临时目录与入口引用；不扫读其他项目全部内容，不清空全局日志/缓存。
2. 持久化源路径到 H 包/成员的总索引、各批完整读取回执、源删除回执、共享保留项和未完成项。重要资产可按阶段/模型名查到；不要只交付一组无索引 tar。
3. 在服务器临时会话目录移除前，先确保控制器、清单、日志与收据已有本地副本。最终删除收据由本机写入 H；仓库轻量结果从本机发布，不重新创建 AutoDL 项目目录。
4. 轻量更新仓库 `results/storage_export/20261118/`、`results/index.json`、AGENTS/README 的真实完成状态；完整清单与大型归档保留 H，不上传 GitHub Releases。公开材料不得包含凭据内容。
5. 报告最终 H 路径、批次数、源文件逻辑大小、传输字节数、完整读取结果、源删除数量与逻辑字节、实际盘空闲变化、专属残留、共享保留与其他任务是否受影响。硬链接/稀疏文件及其他任务活动可能导致释放空间不同于逻辑删除量，应如实解释。

仅在实际完成后标记 `completed`。否则使用准确状态，如 `planned_access_blocked`、`inventory_complete`、`copying`、`incomplete`；逐项可用 `verified_local`、`deleted_source`、`shared_retained`、`deferred_active`。不能以已生成计划、已推送 GitHub、历史归档完成或未来预期代替本次完成证据。

## 6. 本次已完成和未完成的工作

已完成：O7 已发布完成状态核查、11 月 11 日两次实际归档/清理记录核查、历史目录格式与新迁出范围梳理、最终迁出任务和本机执行提示词。

未完成：H 盘现场读取、D57 现场进程/文件/依赖核查、新增归档、传输、逐包完整读取、源文件删除和最终残留清零。它们需要本机执行端继续，**不是等待用户再次授权**。

执行提示词：[FINAL_ARCHIVE_CODEX_PROMPT_20261118.md](FINAL_ARCHIVE_CODEX_PROMPT_20261118.md)。机器可读计划：[final_evacuation_plan.json](../results/storage_export/20261118/final_evacuation_plan.json)。
