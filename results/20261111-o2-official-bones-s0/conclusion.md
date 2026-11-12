# O2 bounded segment results and 2026-11-12 review

O2 training, all three saved checkpoints on both libraries, and lightweight publication are completed.

| Checkpoint | BONES return | Complete / 130394 | Failures | Hard complete /639 | LAFAN cross-library return | LAFAN complete /40 |
|---|---:|---:|---:|---:|---:|---:|
| hour_03 | 0.93501955 | 130215 | 179 | 552 | 0.62306608 | 25 |
| hour_06 | 0.87472977 | 129997 | 397 | 597 | 0.62468111 | 26 |
| final | 0.62929250 | 83910 | 46484 | 127 | 0.03270170 | 0 |

**Preserve hour_03 as the quality anchor and hour_06 as the difficult-motion coverage reference.** The 3h checkpoint exceeds the paper's SONIC return reference of0.90 on this project's full library. The author's25/129514 failure result is a separate reference with unresolved exact member alignment. The final regression does not revoke the saved3h result.

All201 score CSVs /391302 rows were independently recomputed with no row or ID-coverage inconsistency. From3h to6h, hard coverage improves while129875 common-complete motions lose return and tracking precision. From3h tofinal,46338 previously complete clips are lost. All494 motions of at least60s completed at3h and6h, but461 fail atfinal.

The reviewed evaluator reloads each checkpoint and its normalizers and uses the official real simulator. No deterministic scoring-wiring error was found.327 sampled training snapshots show improving local WM fitting/imagined objective statistics while formal behavior worsens; the unique training cause is not established.

O3 is a planned matched weights-only warm-start comparison from hour_03: original fixed LR2e-4 versus quarter LR5e-5, each up to32000 new joint updates, sharing one8h campaign training deadline. O3 adapters and execution have not started in this review turn.

[Detailed review](../../docs/O2_REVIEW_20261112.md) · [Derived data](review_20261112.json) · [O3 plan](../../docs/O3_OFFICIAL_BONES_STABILITY_PLAN.md)

O1/P6 LAFAN acceptance remains intact. Large weights, arrays and logs remain on D57. No historical cleanup, automatic extension or P12 restart.

