# O6 actual results

Status: **completed**; training **completed**. Updated 2026-11-17T08:06:08.851313+08:00.

Completed collections 320000/320000; actual joint updates 127997; real transitions 1310720000.
Fresh seed0 WM/Actor/Critic/normalizers/optimizer/replay/sampler. parent=null; no historical weights or statistics loaded.
One BONES130394 run, GenCoord/proprio/history10, 4096 envs; all Adam WD0. Initial LR2e-4, collection-clock cosine to6e-6 at250k, then floor to320k.
The collection budget determines completion; 127997 joint is an expectation, never an extra stopping requirement.
No wall deadline or return early stop; real failure is retained without automatic training restart.

| Node | Library | Collection | Actual joint | R | Complete / all |
|---|---|---:|---:|---:|---:|
| collection_080000 | bones_full | 80000 | 31997 | 0.92271856 | 130230/130394 |
| collection_080000 | lafan40_cross_library | 80000 | 31997 | 0.59048894 | 22/40 |
| collection_160000 | bones_full | 160000 | 63997 | 0.94590266 | 130329/130394 |
| collection_160000 | lafan40_cross_library | 160000 | 63997 | 0.61434224 | 23/40 |
| collection_250000 | bones_full | 250000 | 99997 | 0.95323218 | 130358/130394 |
| collection_250000 | lafan40_cross_library | 250000 | 99997 | 0.64936696 | 25/40 |
| collection_320000 | bones_full | 320000 | 127997 | 0.95366549 | 130355/130394 |
| collection_320000 | lafan40_cross_library | 320000 | 127997 | 0.65519185 | 26/40 |

Collection80k/160k/250k/320k and the unique actual endpoint are scored after child exit: one BONES worker, then one LAFAN40 worker.
Final aliases are deduplicated. Initial random-model scores are not scheduled.
Same formal BONES rollouts retain fixed IDs63672/16/101155/124371 stride5 quality series and up to8 final failure windows.
Formal returns accumulate every physical transition. Fixed examples are diagnostic, not representative random samples.
Adjacent and historical comparisons report full-library coverage and common-complete R/XY/body orientation; the final comparison emphasizes250k→320k.
LAFAN is cross-library scoring. O1/P6 acceptance remains valid; P12 paused. No O7 is scheduled.
Large checkpoints/logs/videos/trajectories remain on D57. No Release, archive or stage cleanup.


Floor phase250k→320k: full-library R 0.95323218→0.95366549; failures 36→39; recovered 11, lost 14.
Common-complete n=130344: R 0.95341878→0.95386253; XY 0.052242→0.051751m; body orientation 0.086183→0.086046rad.
The floor phase did not maintain every listed quality/coverage metric; retain the individual changes above.

This is one complete chosen fresh Adam/cosine recipe, not an isolated cosine ablation or an exact recovered author run. No cross-seed or longer-budget stability claim.
