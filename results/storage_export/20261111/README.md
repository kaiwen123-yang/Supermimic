# Supermimic H-drive export, 2026-11-11

Status: running. Snapshot: 2026-11-11T17:16:06.799734+08:00.

This is the user-authorized one-time migration, not the normal experiment publication workflow.
Local destination: `H:\Supermimic`. Full frozen file manifests, confirmations and exact deletion receipts remain in `00_inventory\20261111_1144`.
8 concurrent transfer sequences and 8 server packing workers, no bandwidth cap; up to two zstd threads per compressed batch. Most NPZ/checkpoint batches use uncompressed tar. Existing archives are transferred directly.
The live initial process check found no Supermimic computation/publication and no P12 worktree. P12 remains reserved, and every batch rechecks live processes/config paths before source deletion.
All parent/final/milestone checkpoints (including P6 B33000, P11 endpoints, P10 control27000 and P9 LAFAN60000), processed backing data, fixed P10/P11 evidence, source, environments, assets and Git/stash remain on D57.

Completed batches: 134/278.
Fully read local archive bytes: 158292270464.
Exported original file bytes: 161039700321.
Actual unlinked source bytes: 161039700321 (logical file sizes; disk free is reported separately).
Exported and kept source bytes: 0.
Last observed server free bytes: 409394552832.

Every deletion follows successful download, identical archive byte counts, full local decompressed read and a fresh file-identity/dependency check. No hashes, simulations, restore tests, package installation, GPU use, directory deletion or Release upload.
All H-drive archives remain until the user decides to remove them. Failed/changed/active files remain on the server; details are in status.json and the local receipts.
