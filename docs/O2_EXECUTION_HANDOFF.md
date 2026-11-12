# O2 official BONES execution

Execution follows the fixed plan commit `df663ae4872c04f23848aaa528a42fb8cf457f93`.
The current phase is recorded in `results/20261111-o2-official-bones-s0/summary.json`.

- Host: `autodl-d57`.
- Existing official workspace: `/root/autodl-tmp/robot-repro/supermimic-official-workspace`.
- Isolated adapter checkout: `/root/autodl-tmp/robot-repro/supermimic-o2-official-bones`, branch `codex/o2-official-bones`.
- Deployed adapters: official workspace `work/o2`.
- Session: `sm-o2-official-bones-s0`.
- Driver: `bash work/o2/run_d57.sh`; from the workspace root. An active session must not be started again.
- Run artifacts: `outputs/o2-official-bones-s0`; logs are `driver.log`, `pack_existing_bones.log`, `train_official.log`, `evaluate_library.log` and `publication.log`.
- Current process: `active_child.json`; lifecycle: `stage.json`; training counters and cumulative seconds: `progress.json`; fixed weights: `nodes.json`.

The driver converts the retained P9 qpos/qvel, publishes the full identity index, and starts a fresh seed0 BONES-only official run.
It waits for the training child to actually exit before creating the BONES evaluator. That worker loads the library once and evaluates each actual saved node. After it exits, a separate LAFAN40 worker evaluates the same nodes. The final publication updates README, AGENTS, results/index and the campaign summary.

Training has a cumulative 43200-second or 1000000-collection limit, including heavy imports, library loading, initialization and compilation. Saves at approximately 3h/6h and final do not start GPU scoring. No O1 success-stop file is consulted. Learning, rewards, failures, normalizers and sampling remain upstream. Ordinary checkpoints retain the latest 20; initial and formal nodes are protected.

At an interaction handoff, leave the active tmux/replay/learning rate intact. A weights-only checkpoint is not full resume. If a real training error occurs, read its failure.json and preserve consumed budget before deciding a recovery; the launcher does not automatically restart training.

Only after a scoring process has actually failed, `--start-at bones` or `--start-at lafan` continues from saved complete batch CSVs. Completed node scores are reused. `--start-at publish` retries publication only after both libraries' scores already exist. Do not use these options while a worker is alive.

Full lightweight indices and score parts enter Git; weights, packed arrays and full logs remain on D57. O1 and historical worktrees, Git/stash, environments, datasets and checkpoints are preserved. No H-drive migration, stage cleanup, new seed/control or P12 launch is included.

## 2026-11-12 scoring continuation

Training ended normally at 10:45 Beijing after 43200.161 seconds, with 325793 collections and 130314 joint learning phases; the child exited with code 0. The 3h, 6h and final weights are protected.

The first BONES evaluation saved batch 0 (4096 clips), then failed at the next batch reset at 10:47. Sensor history had been created inside PyTorch inference mode, but the batch reset mutated it outside that mode. The adapter now runs the entire scoring batch, including reset, inside inference mode. Official physics, reward, failure conditions, model weights and training are unchanged.

Continue with `bash work/o2/run_d57.sh --start-at bones` only after confirming the old driver/evaluator has exited. The existing batch 0 CSV is read directly, and actual scoring resumes at batch 1. Validation uses the remaining formal evaluation; no extra tests, replay or training are added. The driver publishes scoring-stage transitions and any actual child failure so the repository status follows the running stage.
