# Migration logging repair, 2026-11-11

The progress check found four completed batches (b0087, b0088, b0090, b0091) incorrectly marked incomplete after `OSError(22, Invalid argument)` during the success log output. The archives had already been downloaded, fully read locally, moved into their final H-drive folders and acknowledged by D57; both ends held matching deletion receipts. The exception handler had overwritten the completed status before its own log output also failed, ending the worker.

The Windows controller now opens its append log directly, instead of using the inherited WSL output channel. Success logging is outside the migration exception handler, and Git publication output uses the same native log handles.

All active old transfers were allowed to finish. The four local archive sizes and confirmations were checked against the identical local/server receipts, and the exact deleted source paths were confirmed absent. Their statuses were restored from these completed transactions. No archive was retransferred and no source deletion was repeated. The stale local migration pane was restarted from the existing 91 completed batches; the four D57 packing workers stayed running. Training was not started, stopped or restarted.

See `logging_recovery.json` for the affected batches and existing deletion amounts. The live local index remains `H:\Supermimic\00_inventory\20261111_1144\summary.json`.
