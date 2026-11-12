# O2 official full BONES

**2026-11-12复核：3h为当前质量锚点，6h为困难覆盖参照。** 全201个评分CSV、391302行已独立重算。3h回报超过SONIC的0.90参照；后期回撤不撤销该节点成果。详见[完整复核](../../docs/O2_REVIEW_20261112.md)、[逐clip衍生统计](review_per_clip_20261112.json)、[O3计划](../../docs/O3_OFFICIAL_BONES_STABILITY_PLAN.md)。O3仅方案发布，尚未启动。

Status: **completed**. Updated: 2026-11-12T12:00:07.468331+08:00.

Fresh seed0, BONES-only 130394 clips, official GenCoord/proprio/history10, 4096 environments.
Training ends at cumulative 43200 seconds or 1000000 collections. No return-based early stop.

| Node | Library | R | Complete / all | Training seconds |
|---|---|---:|---:|---:|
| hour_03 | bones_full | 0.93501955 | 130215/130394 | 10800.3 |
| hour_03 | lafan40_cross_library | 0.62306608 | 25/40 | 10800.3 |
| hour_06 | bones_full | 0.87472977 | 129997/130394 | 21600.2 |
| hour_06 | lafan40_cross_library | 0.62468111 | 26/40 | 21600.2 |
| final | bones_full | 0.62929250 | 83910/130394 | 43200.0 |
| final | lafan40_cross_library | 0.03270170 | 0/40 | 43200.0 |

Training checkpoints are saved before scoring. A BONES worker scores all saved nodes only after the training child exits; a separate LAFAN40 worker follows.
All scored clips, including failures, are retained in each node's CSV parts. Dataset indices preserve original BONES IDs.
R>0.90 is the SONIC reference. The author's 25 failures use 129514 clips; exact member alignment remains unresolved.
LAFAN is a cross-library evaluation of a BONES-only fresh model. O1 and the existing LAFAN acceptance remain unchanged.
Large weights, packed arrays and full logs remain on D57. No automatic extension, next run, archive or stage cleanup.

