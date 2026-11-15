# O5 actual-node results

Status: **evaluating_lafan**. Training: **completed**. Updated: 2026-11-16T00:37:28.784707+08:00.

O3 quarter/update_32000 WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG. full_resume=false.
Fixed LR=5e-5; 4096 environments per arm; updates per arm {'muon_wd0': 32000, 'adam_wd0': 32000}, target 32000 each; total 64000/64000.
muon_wd0 preserves official grouping and removes Muon decay; adam_wd0 uses all-parameter Adam with zero decay.
No wall-clock deadline or return-based early stop. Saves: initial/8k/16k/32k and actual final for each arm.
Ancestor 63924 updates are provenance only. Failed/interrupted training is never restarted automatically.

| Node | Library | New updates | R | Complete / all |
|---|---|---:|---:|---:|
| muon_wd0/update_08000 | bones_full | 8000 | 0.93653324 | 130274/130394 |
| muon_wd0/update_08000 | lafan40_cross_library | 8000 | 0.65242988 | 27/40 |
| muon_wd0/update_16000 | bones_full | 16000 | 0.92026524 | 130314/130394 |
| muon_wd0/update_16000 | lafan40_cross_library | 16000 | 0.66535984 | 29/40 |
| muon_wd0/update_32000 | bones_full | 32000 | 0.91915658 | 130344/130394 |
| muon_wd0/update_32000 | lafan40_cross_library | 32000 | 0.65878705 | 26/40 |
| adam_wd0/update_08000 | bones_full | 8000 | 0.92371814 | 130254/130394 |
| adam_wd0/update_08000 | lafan40_cross_library | 8000 | 0.62055261 | 25/40 |
| adam_wd0/update_16000 | bones_full | 16000 | 0.93826439 | 130268/130394 |
| adam_wd0/update_16000 | lafan40_cross_library | 16000 | 0.63163493 | 25/40 |
| adam_wd0/update_32000 | bones_full | 32000 | 0.92838634 | 130304/130394 |
| adam_wd0/update_32000 | lafan40_cross_library | 32000 | 0.63282244 | 24/40 |

Initial scores reuse O3 quarter32k: BONES R=.94430475, 130307/130394 complete, 87 failed. Final aliases are evaluated once.
Quarter16k remains the quality anchor (R=.94757578). Historical O4: 16k R=.92672114/71 failed; 32k R=.90437763/93 failed; reuse without simulation. O2 remains a separate historical reference.
Training must exit before one BONES worker scores all actual nodes, followed by one LAFAN40 worker.
Every node includes parent/within-arm-adjacent comparisons, common-complete quality, hard/skills/duration and frozen failure groups. Equal-update arms and parent+O4+A+B intersections are under comparisons/.
Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals.
LAFAN is cross-library scoring after BONES-only training. Existing O1/P6 acceptance is preserved.
Each arm actual final retains at most eight short failure windows from the same evaluation; no extra rollout or prediction.
Large artifacts remain on D57; no Release, archive, stage cleanup or next stage is scheduled.


Training target reached: True; continuous updates: {'muon_wd0': 32000, 'adam_wd0': 32000}.
muon_wd0/update_08000 versus_O3_quarter_update_32000: R change=-0.00777151; newly complete=48, lost=81.
muon_wd0/update_16000 versus_O3_quarter_update_32000: R change=-0.02403951; newly complete=65, lost=58.
muon_wd0/update_16000 versus_previous_node: R change=-0.01626799; newly complete=76, lost=36.
muon_wd0/update_16000 versus_historical_O4: R change=-0.00645590; newly complete=50, lost=59.
muon_wd0/update_32000 versus_O3_quarter_update_32000: R change=-0.02514817; newly complete=80, lost=43.
muon_wd0/update_32000 versus_previous_node: R change=-0.00110867; newly complete=64, lost=34.
muon_wd0/update_32000 versus_historical_O4: R change=+0.01477895; newly complete=83, lost=40.
adam_wd0/update_08000 versus_O3_quarter_update_32000: R change=-0.02058661; newly complete=51, lost=104.
adam_wd0/update_16000 versus_O3_quarter_update_32000: R change=-0.00604036; newly complete=57, lost=96.
adam_wd0/update_16000 versus_previous_node: R change=+0.01454624; newly complete=77, lost=63.
adam_wd0/update_16000 versus_historical_O4: R change=+0.01154324; newly complete=40, lost=95.
adam_wd0/update_32000 versus_O3_quarter_update_32000: R change=-0.01591841; newly complete=56, lost=59.
adam_wd0/update_32000 versus_previous_node: R change=-0.00987805; newly complete=84, lost=48.
adam_wd0/update_32000 versus_historical_O4: R change=+0.02400871; newly complete=80, lost=77.
muon_wd0 +16000 versus_O3_quarter_update_32000, common-complete n=130249: R 0.94485519 → 0.92077049; XY 0.071845 → 0.128490 m; body orientation 0.099971 → 0.118264 rad.
muon_wd0 +16000 versus_previous_node, common-complete n=130238: R 0.93719120 → 0.92077978; XY 0.088971 → 0.128501 m; body orientation 0.109184 → 0.118284 rad.
muon_wd0 +16000 versus_historical_O4, common-complete n=130264: R 0.92717118 → 0.92072199; XY 0.107271 → 0.128544 m; body orientation 0.113107 → 0.118343 rad.
muon_wd0 +32000 versus_O3_quarter_update_32000, common-complete n=130264: R 0.94480222 → 0.91951783; XY 0.071918 → 0.122262 m; body orientation 0.100029 → 0.122408 rad.
muon_wd0 +32000 versus_previous_node, common-complete n=130280: R 0.92068661 → 0.91949695; XY 0.128585 → 0.122252 m; body orientation 0.118374 → 0.122452 rad.
muon_wd0 +32000 versus_historical_O4, common-complete n=130261: R 0.90493371 → 0.91954890; XY 0.161969 → 0.122186 m; body orientation 0.131260 → 0.122274 rad.
adam_wd0 +16000 versus_O3_quarter_update_32000, common-complete n=130211: R 0.94491079 → 0.93897708; XY 0.071797 → 0.090100 m; body orientation 0.099946 → 0.105399 rad.
adam_wd0 +16000 versus_previous_node, common-complete n=130191: R 0.92447561 → 0.93901206; XY 0.136115 → 0.090064 m; body orientation 0.117327 → 0.105392 rad.
adam_wd0 +16000 versus_historical_O4, common-complete n=130228: R 0.92722189 → 0.93893924; XY 0.107225 → 0.090158 m; body orientation 0.113082 → 0.105460 rad.
adam_wd0 +32000 versus_O3_quarter_update_32000, common-complete n=130248: R 0.94485711 → 0.92890414; XY 0.071837 → 0.109658 m; body orientation 0.099964 → 0.117327 rad.
adam_wd0 +32000 versus_previous_node, common-complete n=130220: R 0.93895412 → 0.92893919; XY 0.090153 → 0.109637 m; body orientation 0.105433 → 0.117337 rad.
adam_wd0 +32000 versus_historical_O4, common-complete n=130224: R 0.90500825 → 0.92897044; XY 0.161890 → 0.109583 m; body orientation 0.131176 → 0.117194 rad.

Fixed32k has a return/precision/parent-retention tradeoff; no single winner is selected.

Use fixed32k and16k→32k trends together; retain coverage/precision tradeoffs. No automatic parent replacement or budget extension.
O4 is historical, not a concurrent randomized control.32k does not prove132k stability or full paper Adam+cosine reproduction.
R=.90 is the SONIC reference; the author25-failure count uses different membership. No cross-seed or permanent-stability claim.
