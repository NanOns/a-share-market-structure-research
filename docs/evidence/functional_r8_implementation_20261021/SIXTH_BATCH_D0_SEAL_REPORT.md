# R8 Batch 06 — D0 Seal audit and evidence

- **Outcome:** `D0_CODE_READY_HISTORICAL_SOURCE_NOT_PROVEN` (state B). This is an external-review handoff, not acceptance.
- **P0 scope:** D0 Seal only. No 28765 production switch, final package, accepted Head update, or production admission.
- **Plan/contract:** `V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md`; successor contract `V4_D0_SOURCE_SEAL_SUCCESSOR_R1` v1.0.0. Formal scenarios are `LAUNCH_CONFIRM` and `RECOVERY_TURN`; `STRONG_PULLBACK` and `TREND_CONTINUE` stay diagnostic-only.
- **Baseline:** branch `codex/v4-unified-development` at `d90aae51eeb39599b7d915191d8822a2895cc0f0`; implementation commit pushed as `ce5f59b5754423183ad0e863a54684b893e93e6b`.

## D0-01 — Formal scenario source mapping

The producer now emits a versioned mapping from each formal scenario check to its input field and source roles. The BFF builds a source map from exact candidate Owner bindings and versioned scanner, producer, detector, parameter and seal-contract bytes. Diagnostic scenarios are explicitly outside formal D0 aggregation. Seal evaluation does not mutate the original row predicate state.

## D0-02 — Candidate source bytes and clocks

For T0 `2026-10-15`, the exact candidate D0 Owner is 5,226 rows, SHA-256 `570f68d3cc90cb68ef6a1102d91d535795ea46920c4ded2a9c6f6b23b574fb99` (2,892,297 bytes). The mapped raw, adjusted, core and scanner/producer inputs are independently byte-bound; their hashes and sizes are in the JSON evidence. The 10/15 TDX SourceIngress artifact reads back as SHA-256 `6ad6620a5e0fdc0128976d8c1f58d77c68626dc59e44ea2a8fcb685c78e2c4c8`, 2,179,581 bytes, 5,565 rows. PG records it as package date 10/21, `available_at=2026-10-21T17:35:26+08:00`, `RECONSTRUCTED_FROM_LATER_PACKAGE`, `RECONSTRUCTED_NON_PIT`; artifact-byte readback is `PASS`. This proves the bytes now present, not historical first availability.

The original tri-state counts remain **FALSE 5,111 / TRUE 64 / UNKNOWN 51**. Across the two formal scenario row sets (5,226 each), both remain `CUTOFF_CONTRACT_UNRESOLVED`; the result labels the source `SOURCE_REPRODUCIBLE_POST_HOC` and `HISTORICAL_FIRST_AVAILABILITY_NOT_PROVEN`. No PIT or `AS_RECORDED` claim is made.

## D0-03 — Independent PG Owner/Publication validation

Read-only PG identity: `127.0.0.1:5432/market_research`, OID `646711`, PostgreSQL `180006`, transaction `read_only=on`. The exact-date query found one SourceIngress receipt and 5,565 rows for its source digest. It found **zero** 10/15 rows in `v4.publications`, D0 `publication_module_results`, and `v4.stock_prewatch_publications`; no consumed-source digest or Owner SELECT permission edge exists. The independently checked D0 state is `PG_BINDING_MISSING` / `permission_chain_proven=false`.

The separate R8 candidate Publication table contains a 10/15 row whose candidate token matches the BFF context token `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`. That confirms the candidate publication identity only; it does not fill the missing D0 Owner/Publication edge.

## D0-04 — BFF and 28766 same-token readback

At `127.0.0.1:28766`, a single context token and T0 `2026-10-15` were carried through Home, stock list, stock profile, Focus and Forward. All returned HTTP 200. Home, stocks, profile and Focus returned `READY`; Forward returned `SOURCE_INCOMPLETE`. Focus returned 30 items in the requested display page while its D0 reason summary covered the full bound 5,226-row Owner. A first post-reload hit exposed an actual BFF serialization failure on PG `inserted_at`; the read-only query now casts that timestamp to text, and the repeated same-token readback passed. Focus seal distribution is 10,452 `CUTOFF_CONTRACT_UNRESOLVED` scenario rows; predicate values remain unchanged. HTTP 200/`READY` are transport/UI readiness only and do not imply a seal or formal Head match. `production_accepted=false`; 28765 was not touched.

Exact payload lengths, hashes, durations and token equality are recorded in `SIXTH_BATCH_D0_SEAL_EVIDENCE.json`. Compact live HTTP receipt: `G:/codex_tmp/sixth_batch_d0_28766/HTTP_READBACK_R2.json`, SHA-256 `E5A789D2B683099A270BCAA211BD513797C6509FD41BDD808F90FCD3E00454F8`.

## D0-05 — Counterexamples and acceptance

The requested negative suite passed **52 tests**. It rejects tampered bytes, caller-supplied hash/permission claims, missing PG Owner/Publication, token/T0 mismatch, unresolved cutoff, reconstructed or late sources, timezone-less timestamps, future-window rows, invalid price coordinate, and diagnostic-scenario promotion. It also confirms post-10/14 dates reach the verifier and D0 tri-state outputs remain unchanged. Python compilation passed.

**Gate result:** code path and verifier are implemented and exercised. Historical source and D0 PG publication evidence remain unproven, so outcome is state B and awaits external audit. This report does not authorize a production Head, 28765 switch, or packaging.

## Next capturable session

`2026-10-22` is the next scheduled weekday session after the 2026-10-21 review. SSE’s 2026 closure notice says regular trading resumed on 2026-10-08 after the National Day closure and gives no intervening closure through 10-22 ([SSE official notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml)). The existing repository calendar contract’s coverage ends earlier, so verify the active official calendar at capture time. No future capture was run in this task.

## Runtime and delivery

- Listeners at final verification: dev API `127.0.0.1:28766`; PostgreSQL `127.0.0.1:5432`; `127.0.0.1:28765` had no listener.
- Targeted suite: `52 passed in 0.73s`; `py_compile` passed.
- Code commit: `ce5f59b5754423183ad0e863a54684b893e93e6b`; the remote development branch was verified at the same SHA after push.
- Evidence JSON: `SIXTH_BATCH_D0_SEAL_EVIDENCE.json`.
- Await external audit.
