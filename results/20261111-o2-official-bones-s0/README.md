# O2 official full BONES

Status: **training**. Updated: 2026-11-12T10:45:01.024657+08:00.

Fresh seed0, BONES-only 130394 clips, official GenCoord/proprio/history10, 4096 environments.
Training ends at cumulative 43200 seconds or 1000000 collections. No return-based early stop.

| Node | Library | R | Complete / all | Training seconds |
|---|---|---:|---:|---:|

Training checkpoints are saved before scoring. A BONES worker scores all saved nodes only after the training child exits; a separate LAFAN40 worker follows.
All scored clips, including failures, are retained in each node's CSV parts. Dataset indices preserve original BONES IDs.
R>0.90 is the SONIC reference. The author's 25 failures use 129514 clips; exact member alignment remains unresolved.
LAFAN is a cross-library evaluation of a BONES-only fresh model. O1 and the existing LAFAN acceptance remain unchanged.
Large weights, packed arrays and full logs remain on D57. No automatic extension, next run, archive or stage cleanup.
