# O4 official BONES continuous low-LR run

Status: **evaluating_bones**. Training: **completed**. Updated: 2026-11-14T01:07:45.672516+08:00.

O3 quarter/update_32000 WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG. full_resume=false.
Fixed LR=5e-5; 4096 environments; 132000/132000 continuous new joint updates.
No wall-clock deadline or return-based early stop. Saves: 16k/32k/64k/96k/132k and actual final.
Ancestor 63924 updates are provenance only. Failed/interrupted training is never restarted automatically.

| Node | Library | New updates | R | Complete / all |
|---|---|---:|---:|---:|
| low_lr/update_16000 | bones_full | 16000 | 0.92672114 | 130323/130394 |
| low_lr/update_32000 | bones_full | 32000 | 0.90437763 | 130301/130394 |
| low_lr/update_64000 | bones_full | 64000 | 0.80227512 | 123339/130394 |
| low_lr/update_96000 | bones_full | 96000 | 0.47643112 | 60091/130394 |

Initial scores reuse O3 quarter32k: BONES R=.94430475, 130307/130394 complete, 87 failed. Final aliases are evaluated once.
Quarter16k remains the quality anchor (R=.94757578). O2 hour03/hour06 are separate historical references.
Training must exit before one BONES worker scores all actual nodes, followed by one LAFAN40 worker.
Every node includes parent/adjacent comparisons, common-complete quality, hard/skills/duration and frozen failure groups.
Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals.
LAFAN is cross-library scoring after BONES-only training. Existing O1/P6 acceptance is preserved.
Actual final retains at most eight short failure windows from the same evaluation; no extra rollout or prediction.
Large artifacts remain on D57; no Release, archive, stage cleanup or next stage is scheduled.
