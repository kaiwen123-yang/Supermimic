# 本机 Codex：最终迁出 AutoDL SuperMimic 到 H 盘

> **本次迁出已执行完成。** 下文保留制定方案时的现场信息。实际迁出范围、核查结果和归档索引见[完成回执](../results/storage_export/20261118/final_evacuation_result.json)。

适用环境：能够同时访问用户真实 `H:\Supermimic` 和既有 SSH 别名 `autodl-d57` 的本机 Windows/WSL。只有 AutoDL 终端或聊天沙箱不能完成双端归档。先读取本机实际路径；不假定 WSL 已挂载 `/mnt/h`。

以下提示词可直接交给本机执行端。用户已明确授权确认本地归档后删除服务器 SuperMimic 专属原件，无需再次请求同样的许可。

```text
继续 kaiwen 的 SuperMimic 最终归档任务，直接执行到可完成的终点。

仓库：https://github.com/kaiwen123-yang/Supermimic
目标：H:\Supermimic
服务器：通过本机已有 SSH 配置连接 autodl-d57，不索取或输出私钥/令牌。

先读取仓库最新 AGENTS.md，以及：
- docs/FINAL_ARCHIVE_TO_H_20261118.md
- results/storage_export/20261118/final_evacuation_plan.json
- results/20261117-o7-official-noise-removal-s0/summary.json
- docs/O7_EXECUTION_HANDOFF.md
- results/storage_export/20261111/README.md、status.json
- results/storage_export/20261111/npz_cleanup/README.md、result.json
不要为更新文件覆盖本机未提交修改，也不要 reset/clean。

用户明确要求：最后一轮已经结束就将 AutoDL 上全部 SuperMimic 内容，
包括系统盘的项目文件、全部源码/Git/环境/资产/缓存/临时产物，迁到 H，
确认后删除服务器专属原件，不能影响其他项目和环境。
本次授权优先于历史“源码/环境/模型留服务器”与“不归档不删除”的默认规则。
用户已决定结束复现，不再训练、评分补跑、启动 O8、恢复 P12 或新增实验。

O7 已发布 commit d36b5b54dd6cf8af5733919f273bd6700a9518c3 显示：
completed，320000 collection / 127997 joint，训练/正式评分/轻量发布均完成。
现场仍需确认无后续相关进程、评分、发布或锁，也无其他项目依赖待删除路径。
若实际任务仍在运行，保留现场并报告真实状态，不杀进程、不重启、不直接删除。

先只读 H:\Supermimic 的现有目录格式、真实卷、文件系统、空闲空间、
00_inventory 下旧会话和 98_incoming 中未完成文件。
可用 scripts/inspect_supermimic_archive.ps1；它只输出元数据，不创建目录或删除。
历史实际会话是 20261111_1144，278 批；后来又完成过 NPZ 清理。
历史容量与剩余量不能当成今天的数据，不覆盖/移动/删除旧 H 包及旧回执。

再在服务器枚举所有 SuperMimic 专属根与外部引用：主项目、P/O 工作树、
supermimic-publications、项目缓存中的工作树、整个 supermimic-official-workspace，
包含 .git/common-dir、未提交/未追踪/忽略文件、stash/reflog/LFS、.venv、.python、
.uv-cache、tools、data、outputs、work、模型/日志/视频/轨迹/原始和处理数据等。
也核查系统盘 /root/.config/supermimic 等真实候选与项目专属外部环境、缓存、
临时文件、符号链接、服务/定时入口；用配置、实际引用和归属判定，不按名字整删。
解析 pyvenv.cfg、解释器链接、editable/.pth、Git common-dir、数据链接和硬链接。

保护共享 Conda base、系统 Python/CUDA/驱动、共享 tools/python、tools/uv-env、
robot-repro/.cache/uv、全局 HF/SSH/gh 凭据，以及 MPC-RL/MCP-RL、π0/π0.5 等。
不要整删miniconda3根/base/共享pkgs，但envs下确属SM独占且无他用的环境仍应迁出。
必要依赖可以保存归档副本，不能据此删除共享原件。
项目凭据仅本机受限权限保存，不输出或上传 GitHub；安全保管不了的项单独报告。
存在其他项目依赖的 SM 路径则保留并写清阻塞，不能擅改其他项目来强行清零。

使用实际开始时间的新会话；沿用 H 现有分类，缺少时再增源码/Git、环境/资产、
系统盘项目内容类别。建立源路径→本地包→成员的完整清单。
控制器和日志放本机，服务器临时控制目录须独立于即将删除的项目与环境。
使用现有工具，不安装升级环境，不运行训练/仿真/恢复演练/hash/smoke/unit等测试。

分批迁移，低优先级并发从1–2路开始；不占满任何一端，不打一个巨型总包，
不照搬旧8路并发。Linux源码和环境以保留路径、权限和链接语义的容器归档，
保存跨包硬链接/外部链接的内容映射，不能只复制链接丢失底层数据。
旧 H 包须完整可读、成员匹配，并将对应本地解码内容与当前源逐字节流比较一致，
删除前确认源仍未变化，才可复用；旧日期/文件名/mtime一致不能代替内容确认。
文件系统不支持超大文件时使用有顺序清单的分片并读完整重组流，不格式化盘。

每批必须：传输结束→字节数一致→在 H 完整读取全部归档内容并成功解码→
内容确认→成员与冻结清单一致→删除前源身份/大小/mtime/类型未变且无使用者→
本地回执持久化→只删除该批精确列出的项目专属源文件。
新包实际启用数据校验的，完整解码须确认内建数据校验成功；不能按扩展名推定。
无数据校验的普通tar/直拷文件，须本地解码内容与源逐字节流比较一致才删除。
这属于必要传输确认，不新增hash脚本、模型测试或恢复演练。
tar -t、文件存在或历史 completed 都不能代替完整读取。
只读验证是迁移必要确认，不运行模型或恢复环境，也不声称通过了未做的校验。
不使用全局通配 rm -rf、find-delete、rsync --remove-source-files 或 tar remove-files。
冻结后新增或变化的文件追加归档；目录在清空后才移除，Git common-dir 最后处理。
遇到失败保留未确认源，继续可独立完成的安全批次，并记录真正未完成项。

最后复查数据盘、系统盘、外部引用、临时目录和项目入口，确保专属残留归零。
通用共享依赖保留；仍有未迁出的专属文件或依赖冲突，不能报告全部完成。
完整清单、读取回执、删除回执和脚本日志保存在 H 的新 inventory 会话。
从本机发布不含秘密的轻量回执到仓库并更新 index/README/AGENTS，
不要把大归档上传 GitHub Releases，不为发布在 AutoDL 重建项目目录。

最终报告：实际 H 路径和结构、批次数和字节数、完整读取结果、删除数量、
实际空间变化、系统盘清理范围、全部残留与共享保留项、其他项目是否受影响。
本次聊天端只做了计划，没有传输或删除；以你现场执行的证据记录结果。
除真实缺少 H/SSH 访问或无法安全处理的具体项外，直接完成已获授权的工作，
不要再次询问“是否开始”或“是否删除已验证的项目专属原件”。
```
