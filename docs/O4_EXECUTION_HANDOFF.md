# O4 official BONES execution handoff

Plan commit: `97593b997dfadbdbd3603b24eec1e933a8138105`. Campaign: `20261113-o4-official-bones-long-s0`.

O4 is running in tmux. The training child started on **2026-11-13 at 12:03:08.648 Beijing time**. Driver PID: **981884**; training PID: **982087**. At **12:07:35**, the same process had completed **622 new joint updates, 1561 collections and 6393856 real transitions**, with 6220 WM batch updates and 12440 Critic minibatch updates. The current phase is training; formal scores remain pending. See the published `launch_status.json` and live D57 `progress.json` for the observation and current progress.

Implementation commit: `73a8b21193168e3692530c306e151e897c125254`, based on the required plan commit. Initial Adam/Muon LR was verified from the actual optimizer metadata for all three networks: 5e-5. All four active normalizers retained count **654630912** and the inherited statistics. The unused velocity-goal normalizer remains at zero, as in the parent. The observed GPU process used **34318 MiB** and no second compute process was present. No environment or data preparation was repeated.

The normal training logs from update 50 to 622 span 189.530 seconds, about **3.018 joint updates/s**. At the 12:07 observation this projects training completion to **2026-11-14 around 00:13 Beijing**, followed by approximately **75–120 minutes** for five-node BONES/LAFAN scoring and publication, giving **01:28–02:13** for all results. This is an early measured estimate, not a deadline; later GPU sharing, throughput and network conditions can move it. O3's six-node BONES/LAFAN workers took 3924.4/1142.7 seconds including their publication.

- Host: `autodl-d57`; tmux: `sm-o4-bones-long-s0`.
- User code: `/root/autodl-tmp/robot-repro/supermimic-o4-official-bones`.
- Official workspace: `/root/autodl-tmp/robot-repro/supermimic-official-workspace`.
- Runtime adapters: workspace `/work/o4`; driver log: `/outputs/20261113-o4-official-bones-long-s0/driver.log`.
- Training run: `/outputs/o4-bones-low-lr-long-s0`; inspect `progress.json`, `train_official.log`, `nodes.json`.
- Python: workspace `/supermimic/.venv/bin/python`. Official source: `/supermimic-o3-stability/src`; research source: `/mjlab_research/src`.
- Existing official source patch is reused without reapplication. O4 sets `self.o3_diagnostics` before collection and reuses unchanged O3 diagnostics, metrics and failure-window helpers from the new user code worktree.

One learner starts from the actual O3 quarter32k checkpoint `checkpoint_000080006.pt`. WM bundle, Actor, Critic and complete normalizer buffers are restored into the existing objects. LR=5e-5 is set before Runner/optimizer/CUDA graph construction. Normalizers continue updating. Optimizer/replay/sampler/RNG are new; `full_resume=false`. The official cold-replay condition is retained without extra prefill or WM-only phases.

The single process performs 132000 new continuous joint updates. Fixed saves are 16000/32000/64000/96000/132000 and the actual final; initial reuses parent scores. The budget has `wall_deadline_enabled=false`, `deadline_epoch=null`, `training_wall_seconds_limit=null`. There is no deadline control branch, return-based early stop or automatic training restart. Parent lineage 63924 is provenance only. Ordinary checkpoints retain the newest 20; initial, fixed, final and referenced nodes are protected.

After `wait()` observes the training child exit, one BONES worker loads the library once and scores all actual unique nodes; a LAFAN40 worker follows. Final aliases are deduplicated. A nonzero exit permits evaluation of actual saved nodes while retaining failed/interrupted training state. `training_finished` means child exited; `training_done` means all 132000 continuous updates completed. Scoring completion cannot turn an interrupted run into successful training.

The evaluator reuses O3's inference-mode rollout, full N−1 denominator, failed-tail zeroing, fixed 4096 sorted batches and inactive padding. Immediate-parent scores use O3 quarter32k; quality-anchor scores use O3 quarter16k; O2 hour03/hour06 paths remain distinct. Every node publishes all per-clip scores and comparisons, fixed failure groups, common-complete quality by skill/hard/duration, and LAFAN cross-library results. Actual final captures at most eight failure windows from the same rollout, without extra simulation or WM calls.

Evaluation and authenticated Git publication use the existing shared `p2-publication.lock`, with one scoring process. Training does not hold that lock. Publication starts from current remote main with a non-force update. It touches only O4 artifacts and current status/index entries; historical worktrees and uncommitted changes remain intact. `--start-at bones`, `--start-at lafan`, or `--start-at publish` are for an observed exited training process and incomplete downstream work, never for restarting training.

No environment installation, data preparation, tests, recovery drills or benchmarks are part of this execution. GPU sharing remains allowed. Large artifacts stay on D57; no archive, Release, stage cleanup, O5 or P12 is started. This chat may end once tmux training is stable; the driver continues the authorized training/scoring/publication sequence independently.
