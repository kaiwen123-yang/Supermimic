# O6 fresh official Adam + cosine

Status: **evaluating_lafan**; training **completed**. Updated 2026-11-17T07:53:07.147215+08:00.

Completed collections 320000/320000; actual joint updates 127997; real transitions 1310720000.
Fresh seed0 WM/Actor/Critic/normalizers/optimizer/replay/sampler. parent=null; no historical weights or statistics loaded.
One BONES130394 run, GenCoord/proprio/history10, 4096 envs; all Adam WD0. Initial LR2e-4, collection-clock cosine to6e-6 at250k, then floor to320k.
The collection budget determines completion; 127997 joint is an expectation, never an extra stopping requirement.
No wall deadline or return early stop; real failure is retained without automatic training restart.

| Node | Library | Collection | Actual joint | R | Complete / all |
|---|---|---:|---:|---:|---:|
| collection_080000 | bones_full | 80000 | 31997 | 0.92271856 | 130230/130394 |
| collection_160000 | bones_full | 160000 | 63997 | 0.94590266 | 130329/130394 |
| collection_250000 | bones_full | 250000 | 99997 | 0.95323218 | 130358/130394 |
| collection_320000 | bones_full | 320000 | 127997 | 0.95366549 | 130355/130394 |

Collection80k/160k/250k/320k and the unique actual endpoint are scored after child exit: one BONES worker, then one LAFAN40 worker.
Final aliases are deduplicated. Initial random-model scores are not scheduled.
Same formal BONES rollouts retain fixed IDs63672/16/101155/124371 stride5 quality series and up to8 final failure windows.
Formal returns accumulate every physical transition. Fixed examples are diagnostic, not representative random samples.
Adjacent and historical comparisons report full-library coverage and common-complete R/XY/body orientation; the final comparison emphasizes250k→320k.
LAFAN is cross-library scoring. O1/P6 acceptance remains valid; P12 paused. No O7 is scheduled.
Large checkpoints/logs/videos/trajectories remain on D57. No Release, archive or stage cleanup.
