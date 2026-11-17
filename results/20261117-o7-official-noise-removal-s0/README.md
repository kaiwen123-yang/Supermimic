# O7 fresh Adam + cosine with collection action noise removed

Status: **evaluating_bones**; training **completed**. Updated 2026-11-17T22:45:23.645516+08:00.

Completed collections 320000/320000; actual joint updates 127997; real transitions 1310720000.
Fresh seed0 WM/Actor/Critic/normalizers/optimizer/replay/sampler. parent=null; no historical weights or statistics loaded.
One BONES130394 run, GenCoord/proprio/history10, 4096 envs; all Adam WD0. Initial LR2e-4, collection-clock cosine to6e-6 at250k, then floor to320k.
Official7e94b0 deletes the extra collection randn_like call. Sensor/reset/DR noise and the clean evaluator are unchanged.
The collection budget determines completion; 127997 joint is an expectation, never an extra stopping requirement.
No wall deadline or return early stop; real failure is retained without automatic training restart.

| Node | Library | Collection | Actual joint | R | Complete / all |
|---|---|---:|---:|---:|---:|
| collection_080000 | bones_full | 80000 | 31997 | 0.93039632 | 130237/130394 |
| collection_160000 | bones_full | 160000 | 63997 | 0.94725309 | 130317/130394 |

Collection80k/160k/250k/320k and the unique actual endpoint are scored after child exit: one BONES worker, then one LAFAN40 worker.
Final aliases are deduplicated. Initial random-model scores are not scheduled.
Same formal BONES rollouts retain fixed IDs16/63672/101155/124371/1216/9457 stride5 quality series and up to8 final failure windows.
Formal returns accumulate every physical transition. Fixed examples are diagnostic, not representative random samples.
Same-collection O6/O7 and adjacent O7 comparisons report coverage, failure identities and common-complete R/XY/body orientation; emphasize250k→320k.
Groups include hard639, four skills, all monkey18/wall12/crutches432 and all494 motions>=60s. Reset shares are not transition exposure.
LAFAN is cross-library scoring. O1/P6 acceptance remains valid; P12 paused. No O8 is scheduled.
Large checkpoints/logs/videos/trajectories remain on D57. No Release, archive or stage cleanup.
