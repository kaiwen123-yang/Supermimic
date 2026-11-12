# O3 official BONES fixed-LR comparison

Status: **evaluating_lafan**. Updated: 2026-11-13T02:03:36.867557+08:00.

Same O2 3h WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG on both arms. full_resume=false.
control: fixed 2e-4; quarter: fixed 5e-5. 4096 real environments each; at most 32000 new joint updates per arm.
Shared campaign training deadline: 2026-11-13T02:31:37.534132+08:00. Initialization and contention are included.

| Arm/node | Library | New updates | R | Complete / all |
|---|---|---:|---:|---:|
| control/update_08000 | bones_full | 8000 | 0.93437496 | 130110/130394 |
| control/update_08000 | lafan40_cross_library | 8000 | 0.62983564 | 23/40 |
| control/update_16000 | bones_full | 16000 | 0.93016247 | 130165/130394 |
| control/update_16000 | lafan40_cross_library | 16000 | 0.64029852 | 26/40 |
| control/update_32000 | bones_full | 32000 | 0.89208292 | 129999/130394 |
| control/update_32000 | lafan40_cross_library | 32000 | 0.58545054 | 22/40 |
| quarter/update_08000 | bones_full | 8000 | 0.94680545 | 130258/130394 |
| quarter/update_16000 | bones_full | 16000 | 0.94757578 | 130300/130394 |
| quarter/update_32000 | bones_full | 32000 | 0.94430475 | 130307/130394 |

Initial scores reuse O2 3h; final aliases are evaluated once. All unique actual nodes and failed clips are retained.
Two training children must exit before the single BONES worker; a separate LAFAN40 worker follows. LAFAN is cross-library scoring.
Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals. Training reward is not formal R.
O2 3h remains the quality anchor: R=.93501955, 130215/130394 complete. O2 6h remains the difficult-coverage reference.
This single-seed weights-only comparison does not establish a unique cause or stability at the old 12h/130314-update scale.
Full weights, packed data and full logs remain on D57. No next stage, archive or stage cleanup is scheduled.
