# O2 official BONES full-library baseline

Status: **plan_published_not_started**. Planned on 2026-11-11 (Asia/Shanghai).

This directory currently records the concrete execution plan. O2 adapters, packed conversion, training and formal evaluation have not yet run. See [execution plan](../../docs/O2_OFFICIAL_BONES_PLAN.md), [protocol](../../configs/o2_official_bones_protocol.json), and [Codex start prompt](../../docs/O2_CODEX_START_PROMPT.md).

| Planned item | Definition |
|---|---|
| Initialization | Fresh seed 0; BONES only |
| Training library | Existing project 130394 clips / 47727908 frames at 50 Hz |
| Official sources | SuperMimic abc124c1 + research mjlab dd51a9f |
| Training | One GPU, 4096 real envs, WM10×2048/config8, Actor4096/H32, proprio/history10 |
| Budget | Up to 12 h or upstream collection limit; fixed 3 h, 6 h and actual final checkpoints |
| Formal scoring | After training child process exits; all BONES nodes first, then LAFAN40 cross-library nodes |
| Metrics | All-clip normalized return, failures, completion and quality; SONIC .90 and author single-GPU 25/129514 failures are distinct references |

There is no O2 score or checkpoint yet. The previous O1 LAFAN success remains preserved. Large outputs will remain in `/root/autodl-tmp/robot-repro/supermimic-official-workspace/outputs/o2-official-bones-s0`; lightweight code/configuration/indexes/all per-clip scores/statistics/conclusions belong in Git. No new archive or cleanup task is included.
