# O4 official BONES long-run continuation

Status: **planned; implementation and D57 training not started**.

One fixed5e-5 run from O3 quarter/update_32000, weights-only warm-start, full_resume=false.
132000 new continuous joint updates; no wall-clock cutoff. Save16k/32k/64k/96k/132k and actual final, evaluate all actual nodes only after training exits.

[Plan](../../docs/O4_OFFICIAL_BONES_LONG_RUN_PLAN.md) · [Protocol](../../configs/o4_official_bones_long_run_protocol.json) · [Codex prompt](../../docs/O4_CODEX_START_PROMPT.md) · [O3 review](../../docs/O3_REVIEW_20261113.md).

Parent ancestry63924 and projected195924 are provenance, not uninterrupted-training counts. Preserve O3 quarter16k/32k, O2 and O1/P6 successes; P12 paused.
