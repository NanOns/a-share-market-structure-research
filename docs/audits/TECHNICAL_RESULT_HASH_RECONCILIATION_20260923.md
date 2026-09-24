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

## Versioned repair progress (2026-09-24)

User-authorized FOCUS-07B-01 work introduced `TECHNICAL_RESULT_CANONICAL_IDENTITY_V2` without changing the accepted technical rows or their registered legacy hashes. The 2026-09-22 object was independently recomputed from its immutable DuckDB backup and PostgreSQL: 6,186 rows, registered legacy hash reproduced, canonical hash `6127166c6e7c49590d2f8f2949e7ea76149e5533c544d1d3784addbdcb53c915` identical on both sides. The backup SHA-256 remains `793dae0682a79aaf7b21366baad39ab899a5b043e9cde06e14fdeb1e92650cac`.

The 2026-09-23 accepted object `result-obj-26d6c569b3493670830a8cedbd177419` has no original DuckDB row copy. Reconstructing JSON text with the checked-in producer serializer exactly reproduces its registered legacy hash `26d6c569b3493670830a8cedbd1774191b05ae044f4ea7c8a3fcc0bc59c3e41c`; the same reconstruction also reproduced the 22 September hash against the independent backup. A content-addressed export of these 6,186 accepted PostgreSQL rows has SHA-256 `ce101e6869493fac53c324d63b92508e65539d0e446bb9d597d36cd35577de39`; its canonical hash is `6fcb56d22e01c628b2d082f7e5324043196c22fa36386a82d7fd661c2be5bca2`.

Both objects now have immutable migration records with source object, legacy hash, canonical hash, reason, evidence hash, contract, and acceptance timestamp in `workbench.focus_technical_identity_migrations`. Focus reads both through full-object canonical recomputation and still rejects a mismatched migration record; a rollback-only tamper check verified rejection and restoration. The accepted `analysis_result_objects` and `technical_result_rows` were not modified. The earlier status above describes the original finding; current scoped status is `KNOWN_2026_09_22_AND_23_OBJECTS_RECONCILED / FUTURE_OBJECT_REGISTRATION_PENDING`. New objects without an accepted migration record continue to fail closed.

The post-sync Focus stage now has an exact-publication automatic registration path for later technical objects. It requires the publication head, successful matching snapshot, producer-format legacy hash equality, a content-addressed evidence export, and an immutable V2 migration row before the technical reader can use that object. The path passed idempotent readback against the 23 September accepted object and rejected a wrong publication; first execution against a genuinely new object remains pending. Registration failure is reported as a separate Focus technical identity degradation and leaves the already accepted P12/PG sync result intact.
