# R8 Batch 07 — D0 cutoff and PostgreSQL closure

- **Outcome:** `D0_CODE_PG_INTEGRATION_PASS_CLOCK_WAIT`. The cutoff contract, D0 PG Owner/Publication relation, restricted independent reader, source checks, and 28766 BFF readback are implemented and exercised. The historical 2026-10-15 input remains `RECONSTRUCTED_NON_PIT`; wait for a truthful same-cutoff capture before claiming a positive PIT seal. This report is for independent audit, not external acceptance.
- **Baseline:** `codex/v4-unified-development` at `f80c783ee06da308a2820abf15c3e6037294f36d`.
- **Implementation commit:** `24973967215035c1c49208c0010791258db02b42`, pushed to `origin/codex/v4-unified-development` at the same SHA.
- **Scope:** D0 Seal only. No accepted Head, production admission, 28765 switch, or final package.
- **Applicable contract:** `V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md` S04. Inherited Phase 0 remains `DEGRADED_PASS`; no general scanner phase was started. The D0 frozen scanner was invoked read-only for the requested independent numerical comparison.

## FR8-D0-B07-01 — Post-close knowledge cutoff: PASS

Contract `V4_D0_POST_CLOSE_KNOWLEDGE_CUTOFF_R1` v1.0.0 defines the cutoff as the timezone-aware `inserted_at` of the exact candidate-token-matched R8 snapshot publication. It does not substitute exchange close, T0 end-of-day, producer invocation time, file mtime, or a caller-supplied time. Each consumed source carries a time role and availability; missing clocks fail closed, and a source later than the snapshot cutoff is `RECONSTRUCTED_AFTER_CUTOFF`.

For the exact 10/15 R8 token `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`, the independent PG reader re-read `inserted_at=2026-10-21T20:07:27.040317+08:00`; both T0 and token matched. The SourceIngress artifact was available at `2026-10-21T17:35:26+08:00`, before that replay snapshot cutoff. Its trusted role is `RECONSTRUCTED_FROM_LATER_PACKAGE` and its evidence class is `RECONSTRUCTED_NON_PIT`, so its timing before the replay freeze does not establish historical first availability for 10/15. The D0 seal correctly stays non-PIT.

The general candidate publisher supports a future same-cutoff dev seal only when candidate `AS_RECORDED` and `PIT_ELIGIBLE` are true, source and membership clocks are timezone-aware and no later than the exact snapshot cutoff, and no late/reconstructed role or evidence class is present. Even that path cannot grant production admission.

## FR8-D0-B07-02 — Real PG D0 Owner/Publication and source consumption: PASS

Migration `027_d0_source_seal_batch07_r1.sql` creates the scoped `v4_r8d0seal_batch07_r1` append-only candidate ledger and a `NOLOGIN` reader role. The D0 publication references the exact R8 candidate token and trade date through a PG foreign key; its consumed-source rows bind Owner role, owner-version token, path, SHA-256, byte count, time role, evidence class, availability, source receipt and cutoff comparison. Its facts table contains the two formal scenario outputs. No generic module-result contract or accepted Head is repurposed.

Latest publication: `D0B07:2026-10-15:c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c:r9`. It records the D0 predicate Owner as 5,226 rows, 2,892,297 bytes, SHA-256 `570f68d3cc90cb68ef6a1102d91d535795ea46920c4ded2a9c6f6b23b574fb99`; the PG fact ledger has 10,452 rows and its row-digest readback is `PASS`. The predicate digest is `74846022967bc8645c395f67be31a9342ffab73c2207114758d8774e59d312c2`.

Consumed inputs include raw and adjusted price Owners, core/relative-strength Owner, D0 predicate Owner, membership snapshot and authority, TDX SourceIngress bytes, frozen scanner, target fact producer, scenario detector, parameters, D0 seal contract, PG producer and reader, BFF source verifier, schema migration, runner and independent verifier. Owner bindings carry their `f0f5107b2512a87b29abcb8b6367c4fb100c636ae5d837ee1e686bb6a7136bd0` version token. The raw price coordinate is `TDX_NATIVE_AFFINE_QFQ`; field lineage records check, actual input field/value, source role, owner SHA/version, predecessor-window role and coordinate.

The independent PG session used database `market_research`, OID `646711`, PostgreSQL `180006`, at `127.0.0.1:5432`; the read transaction reported `transaction_read_only=on`. It executed `SET ROLE v4_r8_d0_seal_reader_r1`, verified `session_user=postgres` and `current_user=v4_r8_d0_seal_reader_r1`, and successfully selected D0 publications/facts, the exact R8 publication and SourceIngress receipt. Exact source bytes rehashed as `PASS`; cutoff and receipt links matched. The custom role is granted read access for this verification and has no login or publication authority.

Earlier append-only candidate revisions remain development audit history; they were never accepted, consumed by a Head, or production-admitted. Revision 9 is the highest exact-date/token revision returned by the verifier and the evidence below.

## FR8-D0-B07-03 — Independent source and predicate validation: PASS

The frozen scanner was run over all 5,226 saved `target_values` rows. Its two formal scenario checks and statuses matched all 10,452 stored outputs exactly; mismatch count is zero. No predicate values were mutated:

- Original D0 tri-state: **FALSE 5,111 / TRUE 64 / UNKNOWN 51**.
- `LAUNCH_CONFIRM`: **FALSE 5,127 / TRUE 48 / UNKNOWN 51**.
- `RECOVERY_TURN`: **FALSE 5,153 / TRUE 22 / UNKNOWN 51**.
- `STRONG_PULLBACK` and `TREND_CONTINUE` remain diagnostic-only and outside formal D0 aggregation.

PG independently recomputed every fact digest. The evidence JSON includes representative field-to-Owner traces and true/false/unknown fact samples, plus source hashes, byte counts, time roles and scenario counts. Historical first availability remains unproven, `AS_RECORDED=false`, `PIT_ELIGIBLE=false`, and production admission is false.

## FR8-D0-B07-04 — 28766 BFF and actual HTTP readback: PASS

The current development service was restarted on `127.0.0.1:28766` to load the repaired code. Context, Home, stock list, Focus, Forward and stock profile returned HTTP 200 with the same 10/15 date and token `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`. Focus reports `CUTOFF_CONTRACT_RESOLVED` and `PG_BINDING_PRESENT` for each scenario. Both formal scenarios report 5,226 `POST_HOC_NON_PIT` rows; `first_break` now accurately identifies `HISTORICAL_SOURCE_RECONSTRUCTED_NON_PIT`.

At final verification, PostgreSQL PID 8640 listened on 5432 and the dev API PID 3108 listened on 28766. No process listened on 28765. The service reported `production_accepted=false`; no production port was opened, stopped or restarted.

## FR8-D0-B07-05 — Counterexamples and targeted regressions: PASS

Real PG readback with wrong T0 or token returned `PG_BINDING_MISSING`. The live evidence run also exercised a fake Owner SHA (rejected as `SOURCE_DIGEST_MISMATCH`), a source one second beyond cutoff (rejected as `POST_HOC_AFTER_CUTOFF`), and a reader-version drift (failed the contract match). Unit regressions cover exact date/token identity, missing/late/reconstructed clocks, tri-state preservation and a valid same-cutoff dev input path.

Targeted command `pytest tests/test_v4_d0_source_seal_r1.py tests/test_v4_d0_source_seal_batch07_pg.py -q`: **18 passed**. Python compilation: **PASS**. This is targeted local evidence, not a CI or external audit result.

## Next gate

`CUTOFF_CONTRACT_UNRESOLVED` and `PG_BINDING_MISSING` are no longer the open implementation state for this exact candidate. Historical 10/15 remains `NON_PIT` because its source was reconstructed from a later package and lacks historical first-availability proof. Keep that classification and wait for an eligible same-cutoff capture; submit this code, PG and 28766 evidence for independent review. Do not switch 28765 or create the final package in this batch.

Machine evidence: `SEVENTH_BATCH_D0_CUTOFF_PG_EVIDENCE.json`.
