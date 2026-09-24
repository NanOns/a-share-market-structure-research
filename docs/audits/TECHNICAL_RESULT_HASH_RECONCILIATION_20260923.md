# Independent audit: PostgreSQL technical result hash reconciliation

Date opened: 2026-09-23

## Scope

Determine why the accepted PostgreSQL `technical_result_rows` object does not reproduce its registered `TECHNICAL_RESULT_V3` value hash after applying the producer's documented JSON normalization and value semantics. Focus may consume these factors only after their result identity is independently reproducible.

This is separate from FOCUS-03's release gate. It does not authorize edits to accepted technical rows, result objects, or source artifacts.

## Evidence

- Accepted publication: `m4-547e88ce22e6d89590876c7ea1d68ca0`, trade date `2026-09-22`.
- Accepted technical object: `result-obj-96a6dbe035d14025db62b71ec11ec90b`.
- Registered semantic contract: `TECHNICAL_RESULT_V3`; schema version `technical-result-rows-v1`; expected rows `6186`.
- Registered value hash: `96a6dbe035d14025db62b71ec11ec90bb12015a921064007f029ecb03c5a458b`.
- PostgreSQL row count and `(security_id, trade_date)` uniqueness checks passed.
- Recalculation using `workbench_analysis.technical._technical_hash` over the PostgreSQL rows, including sorted compact JSON normalization for `quality_codes` and `basis_json`, produced `5f5affd051b7a4ca2fb333b03fee7ba44a87e77650736f5f3056b32baf90b9a2`.
- Registered and recomputed value semantics are equal. The recomputed logical row hash is `eaf24782ef1924984de6c41a4b2f227e201f124fd675054ff1be15dcb99bd1f6`; the binding declares `13c217e19249068cad311b095ae27886c0b3f5f23cd99f4e455f565a7a8a95fd`.
- The mismatch blocks technical-factor reuse in Focus. No accepted data was changed.

## Reconciliation finding (2026-09-23)

- The immutable maintenance backup `runtime/manual_delete_backups/trade_date_2026-09-22_20260922T144602Z/market_research.duckdb` contains all 6,186 rows for this exact object. Its SHA-256 is `793dae0682a79aaf7b21366baad39ab899a5b043e9cde06e14fdeb1e92650cac`.
- Re-running the original producer `_technical_hash` over those backup rows reproduces the registered value hash exactly: `96a6dbe035d14025db62b71ec11ec90bb12015a921064007f029ecb03c5a458b`.
- A read-only row-by-row comparison against PostgreSQL found identical business keys and identical values for every non-JSON column. The only physical representation differences are `quality_codes` and `basis_json` on all 6,186 rows: the backup stores serialized JSON text, while PostgreSQL `jsonb` returns decoded arrays/objects. Parsing the backup strings yields semantic JSON equality for all 6,186 rows.
- Root cause: migration storage-type conversion from text-encoded JSON to `jsonb` changed the strings included by the original value hash. The original registration path preserves string input in `_json_text`, so its declared `SORTED_COMPACT_JSON` behavior did not canonicalize already-serialized source strings. PG recomputation then canonicalized decoded JSONB values to compact sorted strings. This is serializer/storage representation drift, not a difference in numeric technical factors or JSON meaning.
- `src/focus_tracker/technical_facts.py` already recomputes the complete object hash before exposing technical facts and fails closed on mismatch. Focus factor state therefore remains `UNAVAILABLE` until an explicitly reviewed repair/versioned identity transition is accepted.
- No PostgreSQL or backup rows were modified. The backup is read-only evidence; the current local DuckDB no longer contains these physical rows.

## Acceptance criteria

1. Reconstruct the original result object's exact canonical row values and documented value semantics from an immutable source/export.
2. Identify whether the discrepancy is a row transformation, serializer/version drift, or an incorrect accepted binding.
3. Independently recompute the registered hash from the accepted physical rows and obtain an exact match, or record a separately approved repair/migration with before/after identities and restore evidence.
4. Add a permanent integrity check at the technical-result read boundary before any consumer treats the factors as accepted.

Status: `ROOT_CAUSE_IDENTIFIED / REPAIR_NOT_AUTHORIZED / FACTORS_FAIL_CLOSED`.
