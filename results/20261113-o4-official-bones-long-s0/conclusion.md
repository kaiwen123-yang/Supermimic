# O4 actual-node results

## 2026-11-15完成复核

O4确实完成132000连续新更新和全部正式评分，但固定5e-5没有保持住长段性能。前16k总失败从87降到71时，同一完整集合的XY已经7.19→10.72cm、R已下降；final R=.62798132、47128失败，较父新完成34、丢失47075。96k→final有部分恢复，不能据此宣布稳定性解决。

保留O3 quarter16k质量锚、quarter32k共同父与O4+16k覆盖参照及全部历史节点。下一轮为同O3父的Muon去衰减/全Adam两路各32k短对照，计划已发布但尚未部署或训练。

- [完整复核](../../docs/O4_REVIEW_20261115.md)
- [汇总派生证据](review_20261115.json)、[全部逐动作配对](review_per_clip_20261115.json)
- [训练诊断复核](training_diagnostics_review_20261115.json)、[优化器源码差异](optimizer_source_audit_20261115.json)、[失败窗口标量](failure_windows_review_20261115.json)
- [O5计划](../../docs/O5_OFFICIAL_OPTIMIZER_PLAN.md)、[O5启动词](../../docs/O5_CODEX_START_PROMPT.md)

以下保留原执行记录，历史句子中的“next stage未排程”指O4发布当时；最新新增计划以上述O5为准。O4不重启、不追加预算。

Status: **completed**. Training: **completed**. Updated: 2026-11-14T01:34:08.622600+08:00.

O3 quarter/update_32000 WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG. full_resume=false.
Fixed LR=5e-5; 4096 environments; 132000/132000 continuous new joint updates.
No wall-clock deadline or return-based early stop. Saves: 16k/32k/64k/96k/132k and actual final.
Ancestor 63924 updates are provenance only. Failed/interrupted training is never restarted automatically.

| Node | Library | New updates | R | Complete / all |
|---|---|---:|---:|---:|
| low_lr/update_16000 | bones_full | 16000 | 0.92672114 | 130323/130394 |
| low_lr/update_16000 | lafan40_cross_library | 16000 | 0.63524271 | 25/40 |
| low_lr/update_32000 | bones_full | 32000 | 0.90437763 | 130301/130394 |
| low_lr/update_32000 | lafan40_cross_library | 32000 | 0.64895802 | 24/40 |
| low_lr/update_64000 | bones_full | 64000 | 0.80227512 | 123339/130394 |
| low_lr/update_64000 | lafan40_cross_library | 64000 | 0.52724380 | 20/40 |
| low_lr/update_96000 | bones_full | 96000 | 0.47643112 | 60091/130394 |
| low_lr/update_96000 | lafan40_cross_library | 96000 | 0.01995162 | 0/40 |
| low_lr/update_132000 | bones_full | 132000 | 0.62798132 | 83266/130394 |
| low_lr/update_132000 | lafan40_cross_library | 132000 | 0.04148550 | 0/40 |

Initial scores reuse O3 quarter32k: BONES R=.94430475, 130307/130394 complete, 87 failed. Final aliases are evaluated once.
Quarter16k remains the quality anchor (R=.94757578). O2 hour03/hour06 are separate historical references.
Training must exit before one BONES worker scores all actual nodes, followed by one LAFAN40 worker.
Every node includes parent/adjacent comparisons, common-complete quality, hard/skills/duration and frozen failure groups.
Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals.
LAFAN is cross-library scoring after BONES-only training. Existing O1/P6 acceptance is preserved.
Actual final retains at most eight short failure windows from the same evaluation; no extra rollout or prediction.
Large artifacts remain on D57; no Release, archive, stage cleanup or next stage is scheduled.


Training target reached: True; continuous updates: 132000.
low_lr/update_16000 versus_O3_quarter_update_32000: R change=-0.01758361; newly complete=71, lost=55.
low_lr/update_32000 versus_O3_quarter_update_32000: R change=-0.03992712; newly complete=74, lost=80.
low_lr/update_32000 versus_previous_node: R change=-0.02234351; newly complete=54, lost=76.
low_lr/update_64000 versus_O3_quarter_update_32000: R change=-0.14202963; newly complete=64, lost=7032.
low_lr/update_64000 versus_previous_node: R change=-0.10210251; newly complete=67, lost=7029.
low_lr/update_96000 versus_O3_quarter_update_32000: R change=-0.46787363; newly complete=42, lost=70258.
low_lr/update_96000 versus_previous_node: R change=-0.32584400; newly complete=2010, lost=65258.
low_lr/update_132000 versus_O3_quarter_update_32000: R change=-0.31632343; newly complete=34, lost=47075.
low_lr/update_132000 versus_previous_node: R change=+0.15155020; newly complete=38112, lost=14937.

Report every node and quality alongside coverage; no automatic parent replacement or budget extension.
R=.90 is the SONIC reference; the author 25-failure count uses different membership. No cross-seed or permanent-stability claim.

