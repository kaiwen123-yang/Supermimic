# O7 actual results

Status: **completed**; training **completed**. Updated 2026-11-17T23:25:48.532916+08:00.

Completed collections 320000/320000; actual joint updates 127997; real transitions 1310720000.
Fresh seed0 WM/Actor/Critic/normalizers/optimizer/replay/sampler. parent=null; no historical weights or statistics loaded.
One BONES130394 run, GenCoord/proprio/history10, 4096 envs; all Adam WD0. Initial LR2e-4, collection-clock cosine to6e-6 at250k, then floor to320k.
Official7e94b0 deletes the extra collection randn_like call. Sensor/reset/DR noise and the clean evaluator are unchanged.
The collection budget determines completion; 127997 joint is an expectation, never an extra stopping requirement.
No wall deadline or return early stop; real failure is retained without automatic training restart.

| Node | Library | Collection | Actual joint | R | Complete / all |
|---|---|---:|---:|---:|---:|
| collection_080000 | bones_full | 80000 | 31997 | 0.93039632 | 130237/130394 |
| collection_080000 | lafan40_cross_library | 80000 | 31997 | 0.59823624 | 23/40 |
| collection_160000 | bones_full | 160000 | 63997 | 0.94725309 | 130317/130394 |
| collection_160000 | lafan40_cross_library | 160000 | 63997 | 0.65359857 | 25/40 |
| collection_250000 | bones_full | 250000 | 99997 | 0.95270039 | 130375/130394 |
| collection_250000 | lafan40_cross_library | 250000 | 99997 | 0.66952625 | 27/40 |
| collection_320000 | bones_full | 320000 | 127997 | 0.95331105 | 130375/130394 |
| collection_320000 | lafan40_cross_library | 320000 | 127997 | 0.67893124 | 28/40 |

Collection80k/160k/250k/320k and the unique actual endpoint are scored after child exit: one BONES worker, then one LAFAN40 worker.
Final aliases are deduplicated. Initial random-model scores are not scheduled.
Same formal BONES rollouts retain fixed IDs16/63672/101155/124371/1216/9457 stride5 quality series and up to8 final failure windows.
Formal returns accumulate every physical transition. Fixed examples are diagnostic, not representative random samples.
Same-collection O6/O7 and adjacent O7 comparisons report coverage, failure identities and common-complete R/XY/body orientation; emphasize250k→320k.
Groups include hard639, four skills, all monkey18/wall12/crutches432 and all494 motions>=60s. Reset shares are not transition exposure.
LAFAN is cross-library scoring. O1/P6 acceptance remains valid; P12 paused. No O8 is scheduled.
Large checkpoints/logs/videos/trajectories remain on D57. No Release, archive or stage cleanup.


Floor phase250k→320k: full-library R 0.95270039→0.95331105; failures 19→19; recovered 9, lost 9.
Common-complete n=130366: R 0.95282485→0.95343114; XY 0.053738→0.051939m; body orientation 0.087467→0.086291rad.
All listed floor-phase metrics maintained/improved.

## O6/O7 at the same completed collection count

| Collection | Library | O6 R | O7 R | O6/O7 failed | Recovered/new/persistent failed | Common n | Common R O6→O7 | Common XY/m O6→O7 | Common body orientation/rad O6→O7 |
|---:|---|---:|---:|---:|---|---:|---|---|---|
| 80000 | bones_full | 0.92271856 | 0.93039632 | 164/157 | 98/91/66 | 130139 | 0.92367273→0.93136418 | 0.127114→0.092439 | 0.112882→0.108725 |
| 80000 | lafan40_cross_library | 0.59048894 | 0.59823624 | 18/17 | 3/2/15 | 20 | 0.77735636→0.78199676 | 2.010821→2.490500 | 0.168991→0.170961 |
| 160000 | bones_full | 0.94590266 | 0.94725309 | 65/77 | 37/49/28 | 130280 | 0.94629051→0.94769693 | 0.064490→0.067581 | 0.094505→0.091009 |
| 160000 | lafan40_cross_library | 0.61434224 | 0.65359857 | 17/15 | 4/2/13 | 21 | 0.81485153→0.81839152 | 1.869691→1.785820 | 0.138818→0.132008 |
| 250000 | bones_full | 0.95323218 | 0.95270039 | 36/19 | 32/15/4 | 130343 | 0.95342402→0.95285056 | 0.052244→0.053709 | 0.086177→0.087455 |
| 250000 | lafan40_cross_library | 0.64936696 | 0.66952625 | 15/13 | 3/1/12 | 24 | 0.81898568→0.81819794 | 1.630025→1.653063 | 0.130985→0.129684 |
| 320000 | bones_full | 0.95366549 | 0.95331105 | 39/19 | 37/17/2 | 130338 | 0.95387307→0.95346516 | 0.051740→0.051900 | 0.086042→0.086275 |
| 320000 | lafan40_cross_library | 0.65519185 | 0.67893124 | 14/12 | 3/1/11 | 25 | 0.82092304→0.81922178 | 1.613935→1.633641 | 0.128604→0.127638 |

| Full fixed group | N | O6/O7 complete | O6 R | O7 R |
|---|---:|---:|---:|---:|
| hard639 | 639 | 611/632 | 0.77720749 | 0.78284688 |
| nonhard | 129755 | 129744/129743 | 0.95453448 | 0.95415052 |
| flip | 44 | 42/43 | 0.77000586 | 0.77168040 |
| side_roll | 22 | 21/21 | 0.74929504 | 0.71235905 |
| cartwheel | 120 | 120/120 | 0.80726279 | 0.81255847 |
| handstand | 160 | 159/159 | 0.72365112 | 0.70207954 |
| monkey_jump | 18 | 1/18 | 0.47092457 | 0.80250232 |
| hook_jump_off_wall | 12 | 9/11 | 0.60464590 | 0.70037245 |
| crutches | 432 | 430/428 | 0.89592191 | 0.89597124 |
| long>=60s | 494 | 494/494 | 0.95379585 | 0.95450286 |

The final node does not jointly reduce failures and retain both common-set R and XY. Report the individual coverage/precision changes as the result.

## O7 late-phase fixed groups (250k→320k)

| Group | Complete250k/320k | All R250k→320k | Common n | Common R250k→320k | Common XY/m250k→320k |
|---|---:|---|---:|---|---|
| hard639 | 632/632 | 0.77917182→0.78284688 | 629 | 0.78539847→0.78916658 | 0.186133→0.178855 |
| nonhard | 129743/129743 | 0.95355496→0.95415052 | 129737 | 0.95363658→0.95422754 | 0.053096→0.051323 |
| flip | 42/43 | 0.75895528→0.77168040 | 42 | 0.78202050→0.78477130 | 0.193144→0.199848 |
| side_roll | 22/21 | 0.72754110→0.71235905 | 21 | 0.73031677→0.73655174 | 0.297032→0.286984 |
| cartwheel | 120/120 | 0.80927909→0.81255847 | 120 | 0.80927909→0.81255847 | 0.189002→0.180062 |
| handstand | 160/159 | 0.70360711→0.70207954 | 159 | 0.70451409→0.70646427 | 0.242444→0.237349 |
| monkey_jump | 18/18 | 0.79666895→0.80250232 | 18 | 0.79666895→0.80250232 | 0.213966→0.209525 |
| hook_jump_off_wall | 9/11 | 0.61575088→0.70037245 | 9 | 0.72969615→0.73418325 | 0.800732→0.656551 |
| crutches | 429/428 | 0.89289148→0.89597124 | 428 | 0.89909067→0.90378578 | 0.185163→0.175319 |
| long>=60s | 494/494 | 0.95531369→0.95450286 | 494 | 0.95531369→0.95450286 | 0.142447→0.148176 |

Per-node paired JSON contains common-set change distributions and recovered/new/persistent failure identities. Six fixed time series are examples, not population estimates. The130394/129514 member alignment remains unresolved.

This is the declared single-seed noise-removal comparison on130394 project motions. Removing the draw changes later RNG consumption. No exact author129514, multi-seed or automatic longer-budget claim.
