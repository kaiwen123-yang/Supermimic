# Transfer concurrency adjustment, 2026-11-11

The user requested a live attempt with 12 transfer sequences, falling back to 8 if unstable, and explicitly selected 8 server packing workers. The first attempt stalled in SSH batch queries while the resumed raw-data transfer continued. It did not sustain 12 payload streams and does not establish a server-wide connection limit.

The current setting is 8 transfer sequences and 8 packing workers, with at most 2 zstd threads per compressed batch and 4 concurrent local full-read processes. The bandwidth cap remains disabled. Packing slots are released as soon as an archive is closed, independently of the subsequent download and local confirmation.

Background SSH queries now use null stdin instead of inheriting WSL input. Query responses carry compact member indices; the full file manifests remain in the local and server batch records. Previously deferred metadata is kept as an earlier attempt when explicitly requeued. Closed archives are reused; the in-progress BONES g1.tar.gz uses SFTP reget only after matching the original remote archive byte size, modification time and inode. No hashes or source-directory deletion were introduced.

The 105 previously completed batches remain recorded. Deferred or interrupted batches were requeued from the same frozen lists, and the raw package prefix was retained across the switch. Current actual totals are in status.json and the live H-drive index.

Observed 8-way payload transfer over 30.0 seconds: 39.53 MB/s aggregate; the preceding 4-way observation was 18.92 MB/s. These are observations during required migration, not a synthetic throughput benchmark. The exact samples are in concurrency_8x8_observation_1.json.
