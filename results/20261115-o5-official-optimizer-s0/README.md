# O5 official optimizer comparison

Status: **evaluating_bones**. Training: **completed**. Updated: 2026-11-15T23:06:39.245772+08:00.

O3 quarter/update_32000 WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG. full_resume=false.
Fixed LR=5e-5; 4096 environments per arm; updates per arm {'muon_wd0': 32000, 'adam_wd0': 32000}, target 32000 each; total 64000/64000.
muon_wd0 preserves official grouping and removes Muon decay; adam_wd0 uses all-parameter Adam with zero decay.
No wall-clock deadline or return-based early stop. Saves: initial/8k/16k/32k and actual final for each arm.
Ancestor 63924 updates are provenance only. Failed/interrupted training is never restarted automatically.

| Node | Library | New updates | R | Complete / all |
|---|---|---:|---:|---:|

Initial scores reuse O3 quarter32k: BONES R=.94430475, 130307/130394 complete, 87 failed. Final aliases are evaluated once.
Quarter16k remains the quality anchor (R=.94757578). Historical O4: 16k R=.92672114/71 failed; 32k R=.90437763/93 failed; reuse without simulation. O2 remains a separate historical reference.
Training must exit before one BONES worker scores all actual nodes, followed by one LAFAN40 worker.
Every node includes parent/within-arm-adjacent comparisons, common-complete quality, hard/skills/duration and frozen failure groups. Equal-update arms and parent+O4+A+B intersections are under comparisons/.
Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals.
LAFAN is cross-library scoring after BONES-only training. Existing O1/P6 acceptance is preserved.
Each arm actual final retains at most eight short failure windows from the same evaluation; no extra rollout or prediction.
Large artifacts remain on D57; no Release, archive, stage cleanup or next stage is scheduled.
