---
stage_id: V4_R21_R4_PREDECESSOR_HEAD_PG_READER_R45_20261017
branch: codex/v4-workspace-cleanup
status: PREDECESSOR_HEAD_PG_READER_CODE_CONNECTED_PENDING_PRODUCER_AND_LIVE_READBACK
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 33
ingress_adapters_open: 8
other_callsite_rows_open: 225
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: connect predecessor authority preparation to its approved publisher and continue period history/verifier and remaining business read migrations
---

# V4 R21-R4 predecessor Head PG reader

Date: 2026-10-17 (Asia/Shanghai). The R44 daily QA PG reader and the current Owner fact contract were reviewed before this change. R45 continues the live `OperationalSuccessorV1.validate()` call chain rather than adding a standalone interface.

## Implemented

- Added versioned `V4_OPERATIONAL_PREDECESSOR_HEAD_PG_R1` fact preparation and read helpers. The helper binds the original source identity and successor accepted T0, verifies its PG descriptor and payload through the existing append-only Owner fact store, and checks the exact predecessor contract.
- Connected successor validation to `read_predecessor()`. If `native_predecessor_head` is embedded, the reader uses the PG route and fails closed on source-binding or fact-key substitution without opening the old artifact. The original `candidate['predecessor']` identity remains unchanged for existing lineage and compare-and-swap behavior.
- The legacy checked-file read remains available only when the successor candidate has not yet been migrated. `prepare()` is an explicit producer ingress helper; no production Head or PG fact was written by this batch.
- Reconciled original baseline row `V4-BCA-R2-c4cd2b4128ff8d81cc54` to implemented PG-only read code pending current Head reconciliation.

## Verification and limits

- Focused R45 tests: **3 passed**. They verify the PG read branch avoids source-file fallback, rejects a changed original binding, and binds the exact legacy source during preparation using controlled Owner-store boundaries.
- Python compilation passed for the new reader and successor validation module. These tests do not prove a live database write/read or full business acceptance.
- No PG connection, Head update, service, market source acquisition or external data write occurred. The accepted Head does not yet embed `native_predecessor_head`; producer integration and live same-T0 readback remain open.
- Period input history/verifier, registry bindings and remaining business callsites are separate open work.

## Accounting

Original P1 baseline remains **266** (200 Owner, 28 other-business, 38 external-source). Formal completion remains **0 / 266**, remaining **266 / 266**. Code-level PG read paths pending reconciliation rise from **32 to 33**. The matrix has **225 OPEN**, **8 ingress adapters open**, and **33 implemented code rows pending reconciliation**; 22 reference edges remain unmapped. This is one code-level row only; no formal P1 item closes.

## Next stage

Connect predecessor fact preparation to the approved successor publisher, then continue source and period-history/verifier migrations. Keep the full live acceptance open until an authorized Reader identity and matching accepted Head are available.
