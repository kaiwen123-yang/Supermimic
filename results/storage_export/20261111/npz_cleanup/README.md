# Authorized follow-up cleanup of historical BONES NPZ files

The user explicitly authorized the 47.53 GB option after reviewing the hard-link audit. Only the frozen per-clip NPZ file list in P8 bones_g1_50hz_full, P8 bones_g1_50hz_40h_s0 and P9 bones_g1_50hz_full_p9 was removed. Directories, manifests, the P9 shared memmap, all protected checkpoints, P4 LAFAN and the O1 workspace were retained.

Before deletion, all 66 corresponding H-drive archives (99538984960 bytes) were fully read with Windows tar -xOf and exited successfully. Their byte sizes matched the original export records. The archive files were rechecked for unchanged size, modification time and file identity after cleanup. H files, including the original migration indexes, were not modified.

Actual deleted file paths: 281356. Their logical sizes total 98961468811 bytes. The last-link removals correspond to 47532883968 allocated file bytes. Filesystem free space changed from 410038497280 to 457533321216 bytes, a net increase of 47494823936 bytes; other server tasks continued running during the operation.

Selected paths remaining: 0. Protected static files unchanged: 275, including 183 checkpoints. No directories, manifests or shared memmap arrays were deleted. Current files remaining from the original 191.45 GB logical retention list: 6858, totaling 92489194148 logical bytes and 92503076864 allocated file bytes.

The original export status.json and H-drive inventory remain historical records of the completed migration. This result.json is the follow-up change in server availability. Original NPZ-based preprocessing or rebuilding the memmap now requires restoring those NPZ files from H; the preserved memmap-based paths and current O1 inputs remain in place. Full per-file manifests and unlink receipts are kept at the C-drive and server paths recorded in result.json, not committed as large Git artifacts.
