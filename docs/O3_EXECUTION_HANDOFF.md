# O3 official BONES execution handoff

Plan: `e517e5c8332559514a6d49ec571aef9df70a04e3`. Campaign: `20261112-o3-official-bones-lr-s0`.

The O3 adapters and identical detached-statistics patch are in `scripts/o3`. Runtime state is authoritative in the campaign summary and D57 outputs. Do not restart active training. O1/P6 acceptance and O2 3h/6h anchors remain protected; P12 remains paused.

- Host: `autodl-d57`; workspace: `/root/autodl-tmp/robot-repro/supermimic-official-workspace`.
- User code: `/root/autodl-tmp/robot-repro/supermimic-o3-official-bones`; deployed wrappers: workspace `/work/o3`.
- Isolated official source: workspace `/supermimic-o3-stability`, base `abc124c1bd5976341034668af3d12c087f2f1f55`; existing mjlab research `dd51a9fcc98791a2f0b018b3c7f71a3eefd5ecdd`.
- Existing Python: workspace `/supermimic/.venv/bin/python`; process `PYTHONPATH` explicitly selects isolated official source and existing research source.
- tmux: `sm-o3-bones-lr-s0`; driver log: workspace `/outputs/20261112-o3-official-bones-lr-s0/driver.log`.
- Run logs/progress/checkpoints: workspace `/outputs/o3-bones-lr-control-s0` and `/outputs/o3-bones-lr-quarter-s0`.
- One persisted shared start/deadline: campaign output `/budget.json`. Read it; never reset it. The driver refuses a repeated training invocation when this file exists.

Both children load the same O2 3h WM/Actor/Critic and normalizer count/moments strictly before collection. LR is fixed before Runner, optimizer and capture construction: control 2e-4, quarter 5e-5. Optimizers/replay/sampler/RNG are new; full_resume=false. No extra fill or warmup was added. The initial checkpoint reuses existing parent scores.

Each child stops at 32000 new joint phases or the shared 8-hour deadline, saving 8000/16000/32000 and actual final. Final aliases reference the same checkpoint and are evaluated once. Parent counts remain separate. Ordinary O3 checkpoints alone retain the latest 20; initial/fixed/final nodes and historical files are protected.

The driver waits for both process exits, then starts one BONES evaluator for all actual unique nodes, followed by one LAFAN40 evaluator. A single existing publication lock covers evaluation and Git publication, never training. Finished batch CSVs and nodes are reused on a scoring or publication interruption. `--start-at bones`, `--start-at lafan`, and `--start-at publish` are the existing bounded continuation entries after inspecting exit/stage records; they do not start training. Actual training exceptions are recorded and do not trigger an automatic unmatched restart.

Collection/reset statistics are device totals since the previous log; imagined dense/bootstrap, survival, raw/clamped values and GAE are the last existing joint-update snapshot. No extra model calls, physics or sampling were added. The upstream CUDA capture behavior and optimizer split remain unchanged. Initial and formal nodes record normalizers, actual optimizer LR, source/import paths and normal resource usage.

Preparation reads three existing O2 checkpoints on CPU and existing console lines. Outputs are `o3_preparation_normalizers.json` and `o3_preparation_existing_real_metrics.json` under the O2 result directory. Historical console episode statistics use the original logger's reset semantics, not O3 all-done accounting or formal R.

Publication uses authenticated `gh` Git-data operations on the current main tree and a non-force ref update. It changes only O3 artifacts, the two O2 preparation tables, current status lines and result index. Uncommitted historical worktrees and stash are untouched. Publication failures keep scores and report pending status; retry publishing without training or scoring again.

Read `summary.json` for the current phase. Training started, training exited, scoring and completed are distinct. Large data/checkpoints/logs remain on D57; no Release, tar, H-drive migration, new stage or budget extension is part of O3.
