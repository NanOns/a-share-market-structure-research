# M7B-07 Recovery and Cleanup Contract v1

Contract: `history-recovery-cleanup-v1.0`.

An M7B history backup is an offline, maintenance-window operation. It copies
the DuckDB file after `CHECKPOINT`, verifies the copied database, and writes an
immutable manifest for every active storage object referenced by the database,
including all registered `analysis_slices`; it does not trust only a payload flag. Each
external object is copied atomically, and both the source and copied bytes are
checked against SHA-256. The TDX root and all paths outside configured managed
write roots are rejected.

The restore drill runs in a new directory outside the workspace root and TDX.
It verifies the database tables, database hash, manifest hash, and every
referenced object hash. The result is written atomically as
`restore_report.json`; a successful drill does not replace the live database.

Cleanup preview is audit-only. An object is protected when it is referenced by
a successful analysis publication, held by an active
history job, covered by an active lease, explicitly referenced by the catalog,
or inside the retention window. A sealed but unbound analysis slice may become
a candidate after retention; unregistered content-addressed files are reported
for manual review. Age alone never authorizes deletion. Existing
quarantine/delete operations remain the only separately confirmed cleanup
actions.

Leases are explicit rows in `leases`, with owner, object IDs, acquisition time,
expiry, and state. An expired or released lease is not a cleanup protection.
Lease acquisition fails for unknown object IDs and release requires the same
owner.

The CLI is:

```text
python scripts/run_m7b_07_recovery.py --as-of YYYY-MM-DD
```

The receipt binds the backup record, restore report, and cleanup reference
audit. It never writes below the TDX root.
