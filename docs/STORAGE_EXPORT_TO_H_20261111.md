# Supermimic 历史数据迁移到 H 盘

日期：2026-11-11（北京时间）。目标：`H:\Supermimic`。

**当前仅已准备执行说明和本地目录创建脚本；本对话未连接 Windows H 盘或 D57 SSH，未实际打包、传输或删除服务器文件。** 由能同时访问本机磁盘和 `autodl-d57` 的本机 Codex 执行本文。GitHub 当前 P12 状态不替代服务器实时进程状态。

## 1. 本次授权及范围

用户明确要求：不影响服务器正常运行和下一轮实验，将原始及过程数据分类导出为归档包，转移到 H 盘；确认转移好的、后续不再依赖的服务器副本删除。本地归档暂时保留，未来由用户决定何时删除。

这是一次独立的存储迁移授权，覆盖旧阶段对“日常自动归档/清理”的默认限制。执行本任务无需再次询问是否允许迁移或删除已经满足条件的过期文件；但不把专项迁移挂到 P12 收尾，也不改变日常 Git 推送后无需本机归档的工作方式。

“全部导出”分为三种明确状态：

- `move_after_confirm`：已结束、不会再写入、当前及下一轮不依赖的历史过程文件。归档和本地转移确认后删除对应服务器文件。
- `copy_only_keep_server`：仍要使用的静态训练数据、父检查点和模型参照。可以导出副本，服务器原路径继续保留。
- `defer_active`：正在训练/评分/发布的 run，及仍在增长的文件。本轮不处理，明确记录待该 run 结束后追加导出的范围，不声称已导出其未来新增内容。

优先处理历史大轨迹、旧检查点、日志和视频，再处理原始下载包和静态工作数据副本。文件名或阶段名包含 P9/P10/P11 不代表可以删除。

## 2. H 盘分类

| 目录 | 内容 |
|---|---|
| `00_inventory` | 原路径与归档对应表、每批文件清单、保护清单、传输及删除记录 |
| `01_source_datasets/BONES` | BONES 原始下载包、原始动作资料 |
| `01_source_datasets/LAFAN1` | LAFAN1 原始数据 |
| `02_processed_data/active_copy_only` | 当前使用的 processed/memmap 备份；服务器不删除 |
| `02_processed_data/retired` | 明确停用的旧处理数据与中间产物 |
| `03_checkpoints/anchors_copy_only` | 父模型、复现达标节点与当前研究参照；服务器保留 |
| `03_checkpoints/historical` | 已结束 run 中可迁走的其他历史检查点 |
| `04_trajectories` | 完整评估、真实采集、想象轨迹及原始数组 |
| `05_logs` | 完整 metrics、stdout/stderr、TensorBoard/event 文件 |
| `06_videos` | 已生成的视频与可迁走的渲染产物 |
| `07_results_and_configs` | 配套配置、manifest、评分、Git 版本信息及恢复位置说明 |
| `98_incoming` | 尚未确认完成的下载文件，完成后移至对应分类 |

各类再按 `campaign/run` 分子目录。不要把所有阶段做成一个巨型包，也不要只按扩展名分类而丢失原始路径。

在 Windows 本机仓库执行：

```powershell
& .\scripts\init_supermimic_archive.ps1 -ArchiveRoot 'H:\Supermimic'
```

脚本只创建目录，不访问服务器、不改已有文件、不发起删除。若本机现有执行方式不允许运行 ps1，直接把文件内容粘贴到 PowerShell，不更改全局执行策略。若执行端为 WSL，先确认实际 H 盘挂载点，再使用对应路径；不能在服务器创建一个名字叫 `H:\Supermimic` 的目录冒充本地存储。

## 3. 明确保留在服务器的对象

以下清单以 P12 已发布依赖为基础。执行时还应纳入服务器上真实正在运行的任务及配置引用，不能只依赖 GitHub 的 planned 标签。

### P12 父模型

```text
/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency/outputs/runs/20261110-p11-root-height-consistency-s0-full8k_residual_control/checkpoint_0036000.pt
```

### 已明确保留的模型参照

```text
/root/autodl-tmp/robot-repro/supermimic-p11-root-height-consistency/outputs/runs/20261110-p11-root-height-consistency-s0-full8k_velocity_height/checkpoint_0036000.pt
/root/autodl-tmp/robot-repro/supermimic-p10-8k-hard-practice/outputs/runs/20261108-p10-8k-hard-practice-s0-full8k_control/checkpoint_0027000.pt
/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/outputs/runs/20261107-p9-critic-full-scale-s0-lafan_h32_control/checkpoint_0060000.pt
```

同时保留已标记的 LAFAN 复现验收节点、当前任务完整恢复所需检查点与现有保护的里程碑/最终权重。不要把“上传到 H 盘”自动解释为允许删除这些保护节点。可以优先迁走未被保护的旧滚动检查点、完整轨迹和大日志，得到实际空间收益。

### 共享数据与实际底层文件

```text
/root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9
```

当前 LAFAN 评分实际引用的 `data/processed/lafan1_g1_50hz` 及真实底层路径同样保留。先根据现有实际配置和符号链接解析依赖，不能保留新工作树中的链接、却删除 P9 的底层文件。静态只读数据允许低负载导出副本，不删除、改名或替换工作数据。

### 固定研究输入、环境与源码

- `configs/p11_fixed_real_windows.json`。
- `results/20261108-p10-8k-hard-practice-s0/jobs/full8k_hard_practice/final_failure_windows/`。
- `results/20261110-p11-root-height-consistency-s0/evidence/full8k_residual_control/`。
- 主项目及各阶段工作树的源码、Git/stash、未提交修改、已追踪 results/configs/docs。
- 现有 `.venv`、`activate.sh`、依赖锁、G1 XML/mesh、运行缓存及共享依赖。
- P12 工作树 `/root/autodl-tmp/robot-repro/supermimic-p12-world-window`。
- 发布锁 `/root/autodl-tmp/robot-repro/supermimic-p6-position-feedback/work/p2-publication.lock` 及其目录。
- 其他项目的所有文件、环境和运行任务。

历史阶段所需的少量固定尾窗已经进入 Git，继续保留。大轨迹可以迁走，但不能连带删掉下一轮要读的这些小输入。

## 4. 只做与迁移有关的现场盘点

在本机确认 H 盘实际存在、文件系统及剩余空间；在 D57 只读取 Supermimic 已知项目根下的 run/数据目录、当前进程/tmux 和实际配置依赖。记录服务器实际可用空间，预留当前及下一轮训练保存检查点所需空间。

不全盘扫描、不读取无关项目内容、不运行模型或环境测试、不安装软件、不做吞吐 benchmark。使用现有工具即可；未知用途文件先保留，其余明确过期的文件继续迁移。

生成一份具体的文件级清单。最少字段：

`source_path, relative_path, category, campaign, run, size_bytes, mtime_ns, action, keep_reason, archive_name`

归档包索引另记：

`archive_name, server_archive_path, local_archive_path, member_list, server_bytes, local_bytes, transfer_status, local_read_status, deletion_status`

清单与状态放 H 盘 `00_inventory`，服务器只留轻量副本。每个归档记录可还原的原始相对路径；避免跟随目录链接重复打包同一套数据。实际删除清单只包含 `move_after_confirm` 的明确普通文件路径，不使用目录通配符。

## 5. 分批打包，训练优先

默认一个低优先级压缩任务与一条传输连接，不使用全部 25 核，不占 GPU。按当前空余磁盘与本地文件系统，通常每批选择约 2–4 GiB 的已封闭源文件；单个更大文件单独处理。文件系统限制及训练增长空间决定实际批次大小，不做容量试跑。若 H 盘是 FAT32，不能写入达到4GiB的单文件；不格式化磁盘，使用现有工具产生每卷不超过2GiB的分卷，并以整组卷完整读取成功为删除条件。现有工具无法处理的大项保留并报告，其余可落盘批次继续；NTFS/exFAT不需要这个分卷步骤。

服务器临时目录可用：

```text
/root/autodl-tmp/robot-repro/supermimic/work/storage_export_20261111
```

采用现有 `tar` 和单线程低压缩级别 `gzip -1`，配合 `nice -n 19`、`ionice -c 3`。低优先级不等于严格的磁盘限速；若已有流量限速工具可以直接使用，不为迁移安装新工具。训练和评分优先，看到现有训练日志持续变慢时暂停迁移/压缩，不暂停训练，不修改训练预算。

以冻结的文件列表归档，保留 root 相对路径，不递归扫入列表外文件；使用 GNU tar 时可用 NUL 分隔列表与 `--null --verbatim-files-from --no-recursion --files-from`。不使用 `--remove-files`。不要重新压缩已有完整原始下载包；直接作为该批归档对象传输。对已压缩的 NPZ/视频，低压缩收益有限，使用 tar 容器即可，不进行压缩率搜索。

临时包先使用 `.partial` 名称，归档命令成功结束且输入无变化后改为固定最终名。源文件此时仍保留。服务器最多保留当前批次的临时/完成包，不先把全部数据压缩一遍把盘塞满。归档占用可能接近未压缩源文件大小，不能用期望压缩比预支训练空间。

不复用训练/评分的发布锁来覆盖数小时传输；迁移由独立会话执行。只在需要正常 Git 提交的短时操作中遵循现有发布协调，避免阻塞正式评分队列。

## 6. 从本机下载到 H 盘

执行位置是能访问 H 盘的本机终端。沿用已有 SSH 别名与认证，不发送密码或私钥到聊天/GitHub。推荐 SFTP 一条连接，初始带宽上限约 20 MB/s：

```powershell
sftp -l 160000 autodl-d57
```

在 SFTP 会话中：

```text
lcd H:/Supermimic/98_incoming
cd /root/autodl-tmp/robot-repro/supermimic/work/storage_export_20261111
get <本批固定归档包名> <本批固定归档包名>.partial
```

中断后仅对同一个已经封闭、未被重建的服务器包使用：

```text
reget <同一个归档包名> <同一个归档包名>.partial
```

`reget` 接续已有本地前缀；若远端包被重新生成，旧 partial 不能用于该新包。为包分配新的唯一名称，不能默默拼接两版内容。SSH alias 若只配置在本机 WSL，就在该 WSL 会话访问已确认的 H 盘挂载点；不要在服务器上调用“下载到 H 盘”。

## 7. 本地确认与精确删除

每批依次完成：

1. 归档生成成功，输入属于已封闭文件，下载正常结束。
2. 比较服务器归档与 H 盘下载文件的字节数。
3. 在本机完整读取一次归档的解压流，确认容器可以读完；输出丢弃，不在 H 盘再生成一份完整解压副本。对 tar/gzip/zip 等本机 tar 支持的格式，可用 Windows `cmd /d /c 'tar -xOf "归档路径" >NUL'`，读取退出码。用现有格式工具处理其他格式。不能把单纯“能看到文件名列表”写成完整内容已确认。
4. 本地文件改为正式名并移到对应类别/campaign/run，记录已完成。这个确认只读本机归档，不跑模型恢复，不做哈希或逐文件摘要扫描。
5. 对 `move_after_confirm` 的冻结源文件清单，结合此时的活跃任务/保护依赖，确认文件仍是当初记录的未变化对象，随后逐文件删除。归档后被修改、重新启用、仍被使用或身份不确定的文件保留并记录原因，不追加到删除集合。
6. 记录真实已删文件与字节数，再删除对应服务器临时归档包。`copy_only_keep_server` 只删除临时包，原文件保留。

禁止用 `rm -rf supermimic*`、整工作树删除、整个 outputs 删除、`find ... -delete`、`rsync --remove-source-files` 或 tar 边压缩边删。不要因为某批失败而停止其他明确可迁移批次；失败批次源文件保留，报告具体原因即可，不造重试系统。

这里的读取确认是本次迁移后删除的依据，不是训练测试。它不产生新的仿真、前向、benchmark 或验证套件。服务器原始文件只有在本机确认后才进入删除操作。

## 8. 交付状态

完成时给出：H 盘实际目录、每批归档对应范围和大小、已导出总量、服务器真实删除量与剩余空间、保护对象和活动 run 的延后范围。

明确区分 `exported_and_deleted`、`exported_kept_on_server`、`deferred_active`、`transfer_incomplete`。有活动 run 时不能把“全部已结束数据完成”写成“整个服务器所有数据都已搬完”。不删除 H 盘归档；用户未来再决定其保留时间。

只向 GitHub 推轻量迁移结论和必要索引，不上传数据包，不创建 Release，也不把本次专项操作变成后续每轮实验的自动步骤。P12 的训练顺序、预算、运行环境和实验配置保持不变。本存储任务本身不启动下一轮训练；已由其他执行会话启动的训练照常继续。

## 9. 交给本机 Codex 的启动提示词

```text
执行 Supermimic 历史数据迁移，目标 H:\Supermimic。
你需要在我的本机环境工作，既能访问 H 盘，又能通过已有 SSH 连接 autodl-d57。
读取最新 main 的 AGENTS.md、docs/P12_WORLD_WINDOW_PLAN.md 和
docs/STORAGE_EXPORT_TO_H_20261111.md，按迁移文档直接推进。

这是我明确授权的一次专项导出：创建分类目录，将已结束实验的原始/过程数据、
旧检查点、完整轨迹、日志、视频及数据归档迁移到 H 盘；确认本地转移完成后，
删除不再被使用的对应服务器文件。当前和下一轮仍需要的数据/模型只备份、不删。
旧的日常“不自动归档/清理”不阻止本次明确任务，也不因此改变以后日常流程。

先核对服务器当前活动任务和具体依赖，不以 GitHub planned/completed 标签代替现场。
保护 P12 当前 run、P11 residual36000父模型、其他已指定模型参照、LAFAN达标节点、
P9共享memmap与LAFAN工作数据、P10固定尾窗、P11父WM证据、环境/G1/源码/Git/stash、
受保护里程碑、发布锁和其他项目。保护真实底层数据，不只保留指向它们的符号链接。

使用 scripts/init_supermimic_archive.ps1 创建 H 盘分类目录。
只盘点 Supermimic 已知数据/产物目录，建立具体文件清单，分别标记
move_after_confirm、copy_only_keep_server、defer_active。
先迁走历史大轨迹/日志/视频及未被保护的旧检查点，再复制静态数据。
活动run整体延后，不搬动正在写入的文件，不让训练等待迁移。

单线程低优先级、小批次归档，传输一条连接，初始约20MB/s。
每批打包成功后从本机下载到H盘，下载成功、字节数一致、在本机完整读取归档一次后，
只删除冻结清单中仍未变化且不再依赖的明确服务器文件，再删除该批临时包。
不使用通配符/整目录删除，不用remove-source-files或边打包边删。
当前输入和保护节点导出后仍留服务器。

不做哈希测试、冒烟测试、恢复模型、benchmark或防御性编程，
不安装重建环境、不重启/停止训练、不改P12预算、不动其他项目。
不占满25核，不占GPU，不持续占用训练发布锁。
若迁移使现有训练持续变慢，暂停迁移，让训练继续。

每批完成更新00_inventory中的索引和删除记录。
本地归档全部保留，未来由我决定删除。
最终报告真实导出量、删除量、剩余空间、仍保留/延后的文件及原因，
把轻量结论推到GitHub，数据包只存在H盘，不上传Release。
已有明确授权的可迁移文件直接做，不反复询问是否开始。
遇到未知依赖文件先保留，继续处理已明确的其他批次。
```

## 参考

- [P12 执行计划及保护依赖](P12_WORLD_WINDOW_PLAN.md)
- [P12 机器协议](../configs/next_stage_world_window_protocol.json)
- [OpenSSH SFTP 手册：限速、get/reget](https://man.openbsd.org/OpenBSD-7.7/sftp.1)
- [GNU tar 文件列表](https://www.gnu.org/software/tar/manual/html_node/files.html)
- [Microsoft New-Item](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item)
