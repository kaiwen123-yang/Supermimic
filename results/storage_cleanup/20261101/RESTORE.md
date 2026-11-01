# Restore SuperMimic on the expanded disk

1. Clone https://github.com/kaiwen123-yang/Supermimic and use the recorded source revision for each run.
2. Download all archive parts from the storage Release in manifest order, verify each SHA256, concatenate them, then decompress with `zstd -d --long=28` and extract the tar inside the project root.
3. For every manifest entry marked `existing_release`, download its exact `remote.url` to the recorded relative path and verify size/SHA256. These files were not duplicated in the archive.
4. Rebuild the isolated environment with `scripts/setup_d57.sh`; dependency locks and the actual installed package list are retained here.
5. Restore input data from the exact revision in `configs/sources.lock.json` with `scripts/prepare_d57.sh`. Raw LAFAN1 is not newly redistributed. Compare regenerated data with `rebuildable_data_files`; retain the original motion manifest recorded here when checking old checkpoints. Do not silently accept a changed dataset hash.

The archive preserves unique outputs and source snapshots; caches and the virtual environment are reproducible, not archived binaries. No MPC/RL, pi-series, shared uv cache, or global Python installation is part of this cleanup.
