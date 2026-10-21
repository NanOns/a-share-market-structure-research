# Fourth Batch Report — R8 Functional Increment (2026-10-21)

## Result

**Status: corrected development append PASS; independent external audit, D0 seal, and market-source gates remain open.** The 2026-10-15 real-source daily increment now completed the full candidate chain: BaoStock retry and TDX reconciliation, exact day freeze, Owner computation and PG payload readback, independent G1–G4 comparator, append-only PG Publication record, development Head CAS, and same-token HTTP acceptance on 28766. The corrected candidate token is `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`; the prior token `ed65f0ff84d2e7f0ed1c7a3c2663a53ee364b951ba8822718ec2ae6dc5e00ed2` is retained as a superseded historical candidate.

The work is candidate-only and `NON_PIT`. The formal Head remains 2026-10-09. No production Head, production service port 28765, scanner, or final production package was changed or accepted. Full machine-readable evidence and copied source receipts are indexed in [ARTIFACT_INDEX.json](FOURTH_BATCH_ARTIFACTS/ARTIFACT_INDEX.json).

## Follow-up repair: D0 aggregation and isolated preview labeling

The prior 10/15 result counted UNKNOWN values from all four D0 branches. The versioned reason-attribution contract marks `STRONG_PULLBACK` and `TREND_CONTINUE` as diagnostic-only; they were incorrectly allowed to override a FALSE result from the two formal branches, `LAUNCH_CONFIRM` and `RECOVERY_TURN`. The repair limits D0 aggregation to those two formal branches and preserves diagnostic outputs in evidence. The saved 5,226-row candidate now recomputes to **5,111 FALSE / 64 TRUE / 51 UNKNOWN**. Of the 51 genuine UNKNOWN rows, 47 lack a valid historical feature window; 11 have no 10/15 bar, while 40 have a bar but incomplete historical/window inputs; 14 also lack CLV (overlapping counts). The old 5,162 UNKNOWN figure overstated formal uncertainty by 5,111 rows.

The corrected candidate was appended with token `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`; G1–G4 comparator status is PASS, the append-only PG ledger now has two rows, and rollback restored the 10/14 last-good Head byte-for-byte. `28766` was restarted and returned the same token with HTTP 200 across nine routes, including priority; the priority response took 138.718 ms and reported `projection_rank_compute_ms=0.0`.

The first same-token HTTP readback, before the corrective restart, exposed a related status-label defect: a candidate Head inside the isolated temporary root was treated as formal acceptance and the response said `production_accepted=true`. This did not change the formal 10/09 Head or start/listen on 28765. `OperationalSuccessorReaderV1` now forces isolated `G:/codex_tmp` roots to candidate-preview semantics, and the R8 bridge rejects a readback that does not report `production_accepted=false` and `DEVELOPMENT_CANDIDATE_PREVIEW`. The original append receipt is preserved unchanged and the discrepancy is explicitly included in its follow-up evidence for independent audit.

## Stage contract and baseline

- Audit start baseline: `codex/v4-unified-development` at `4c65039b7935ea2396740df8552045afcd8afb61`.
- Phase 0 ended `DEGRADED_PASS`; no scanner work was started.
- The 2026-10-18 development high-privilege SOT R2 authorized bounded development PostgreSQL DDL/DML, migration, backfill, recomputation, and development Head/CAS validation. No repeated database write request was made.
- All new workspaces and temporary evidence remained under `G:/codex_tmp`; TDX source roots were read-only and report zero writes.
- Formal accepted predecessor: 2026-10-09. The candidate workspace predecessor was 2026-10-14, explicitly `NON_PIT`; it was not substituted for the formal predecessor.

## BaoStock retry and 351-code reconciliation

10/15 initially failed with provider error `10002007` (`网络接收错误`) at 18:02 China time. A bounded retry found a stale zero-byte session-lock marker left by a stopped diagnostic process; after removing that task-created marker, the 18:32 retry succeeded using the same BaoStock SDK/host. The accepted raw response contains 5,226 daily rows and 22 factor rows. The 10/14 source followed the same transient receive/login-failure pattern and later succeeded at 17:47 on 10/20. Receipts and raw responses for both dates are copied under `FOURTH_BATCH_ARTIFACTS`.

The 351 unmapped TDX rows are **not all BSE**: 350 are `BJ.*` and one is `SZ.301569`. Per the user’s direction, all 350 BJ rows were excluded from this candidate’s SH/SZ calculation universe. `SZ.301569` is an observed 10/15 code and was admitted through the existing date-bounded stable-identity contract; no pre-observation history was invented. Eleven existing identities had no TDX bar and each BaoStock row reported `tradestatus=0`; they are treated as suspended, not inferred as data gaps. The daily scope is therefore 5,215 traded bars plus 11 suspended identities (5,226 total).

## Owner, PG Publication, and Head/CAS bridge

The existing Owner builder was reused and the missing R8 publication bridge was implemented in `src/workbench_db/v4_r8_publication_bridge_v1.py`. The bridge requires a validated single-session candidate, byte-bound G1–G3 evidence, a real CAS rollback drill, exact-token 28766 readback, and a PG append/readback before it records a committed publication. Its development-only schema is `v4_r8pub_fde08c597fc76d13`; `r8_publications` has an append-only trigger. The actual row binds the candidate token, previous and new Head hashes, native Owner authority, source freeze, and HTTP readback.

- Owner computation: 5,226 objects, 5,215 raw traded rows, zero Core calculation errors; exact coordinate Core and downstream Profile/Structure, Sector/Market, and Focus/Forward stages completed.
- Owner PG full-payload preparation: 20 newly created dated facts, 148 immutable facts reused, with exact readback.
- Period numeric oracle: **219,464 checks, zero errors**, based on saved daily history bytes.
- PG Publication ledger: **two append-only rows** (the superseded candidate and corrected candidate), exact readback PASS, append-only trigger present; database `127.0.0.1:5432/market_research`, OID `646711`, PostgreSQL 18.6.
- Failure drill: deliberately rejected same-token readback; 10/14 candidate Head and joint bytes restored exactly, no PG Publication row inserted, transaction state `ROLLED_BACK`.
- Successful development CAS: `APPLIED`; the 10/15 candidate Head hash equals its context token. The formal 10/09 Head remained unchanged.

### Independent append gates

The persisted `V4_R8_CANDIDATE_APPEND_COMPARATOR_R2` evidence reports all four gates PASS for the one-session append:

| Gate | Result | Bound evidence |
| --- | --- | --- |
| G1 | PASS | Shared formal/candidate history business bindings match exactly. |
| G2 | PASS | Historical identity source bytes match by path, size, and SHA-256. |
| G3 | PASS | Source digest recomputed from seven exact source bindings, generation parameters, append window, and previous reference. |
| G4 | PASS | PG Owner/Publication row, exact PG readback, single-session CAS, rollback proof, and same-token HTTP receipt. |

The formal predecessor remains separately bound as 2026-10-09. The 2026-10-14 development predecessor is identified as non-PIT and was used only to extend its candidate chain by one session.

## 28766 and precomputed performance

The development preview was restarted on the **only** development web port, `127.0.0.1:28766`, after CAS so the server loaded the new exact candidate token. After the isolated-root preview label fix, all nine routes returned HTTP 200 with `T0=2026-10-15`, the same token, `read_scope=DEVELOPMENT_CANDIDATE_PREVIEW`, and `production_accepted=false`: `/api/v4/context`, `/api/operations/status`, `/api/v4/home`, `/api/v4/market`, `/api/v4/stocks`, `/api/v4/sectors`, `/api/v4/focus`, `/api/v4/forward/statistics`, and `/api/v4/radar/priority`.

The corrected token R2 read index is sealed in PG and reads back 5,226 stocks, 400 sectors, 404 Focus rows, and 367 radar rows. Priority was precomputed offline for 5,226 stocks (701 rankable) and 400 sectors (121 rankable) in 16.112 seconds. The post-fix same-token priority request returned 200 in 138.718 ms with `projection_rank_compute_ms=0.0`. The earlier 3,355 Focus / 165 radar counts belong to the superseded token. The precompute selects snapshots by token, preserving the prior 10/14 snapshot when a later date is added. Candidate lifecycle reconstruction no longer has a 10/14 date cap.

## D0, market source, and limits

The 10/15 D0/Prewatch/market computation completed but correctly remains source-limited: corrected D0 reports 64 TRUE, 5,111 FALSE, and 51 UNKNOWN; the prior 5,162 UNKNOWN was an aggregation defect, its seal state is null, and market trend remains `UNKNOWN_REFERENCE_PATH_NOT_COMPLETE_AT_T0` (`market_status=SOURCE_INCOMPLETE`). No composite market permission or D0 seal permission was inferred. Repairing those actual-reference inputs remains the next engineering scope; this candidate append does not claim that gate is closed.

## D0 seal and market-source closure analysis

The remaining OPEN items are separate source-governance gates, not database-write authorization blockers. The 2026-10-18 SOT R2 already authorizes the needed development DB operations. The corrected D0 row counts and successful G1–G4 append do not themselves seal the source history.

**D0 seal:** the 10/15 formal scenario rows currently carry predicate checks and outcomes, but not the required `source_available_at`, `knowledge_cutoff`, `input_publication_id`, `time_role`, and source hash fields on each formal evidence record. The existing verifier in `r6_reason_attribution.py` also refuses dates after 10/14 and hard-codes permission as unproven until it reads the actual PG Owner/Publication binding. Therefore, the current implementation cannot close a 10/15 seal even if the D0 predicate outputs are correct. Upgrade the audit contract for 10/15, bind real source clocks and exact bytes for `LAUNCH_CONFIRM` and `RECOVERY_TURN`, then validate the matching PG Owner/Publication permission record. A later download/capture time must not be backfilled as proof of T0 availability.

**Market source:** the candidate binds `V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz`, which has 786 dated rows from 2023-07-04 through 2026-09-24 and no row for 2026-09-25 through 2026-10-15. The 10/15 candidate Market Owner separately carries a WEAK/OBSERVED trend value, but R7 market-stress requires its own same-series reference and source permission chain; its current result correctly remains SOURCE_INCOMPLETE. Its verifier also hard-codes PG permission as unproven. Extend or version the authoritative series through 10/15, bind the calendar, series/version, price basis, close/MA inputs, source hash/times and actual PG publication/permission record, then recompute and compare.

**Closure order:** (1) version the D0 audit to cover 10/15 and attach verifiable source clocks and PG Owner/Publication evidence; (2) extend/freeze the same-series market reference through 10/15; (3) replace the hard-coded permission stubs with actual PG-backed checks; (4) recompute and independently compare both candidate gates, then read the same token on 28766. If original 10/15 availability cannot be proven by the declared cutoff, leave that historical seal OPEN and begin a fully clocked chain on a later session. This work can close candidate provenance only; retrospective membership remains non-PIT and no production admission follows. Full findings and file hashes are in `FOURTH_BATCH_ARTIFACTS/20261021_D0_MARKET_SOURCE_CLOSURE_ANALYSIS_R1.json`.

## Verification and handoff

- G1–G4 business comparator: PASS.
- Source ingress exact-value readback and idempotent replay: PASS for 5 receipts / 27,832 bars, as documented in `PG_SOURCE_INGRESS_EXACT_READBACK_RECEIPT.json`.
- Candidate Head, PG ledger row, read index, period oracle, rollback proof, priority snapshot, BaoStock receipts/raw responses, and live 28766 route measurements are committed in `FOURTH_BATCH_ARTIFACTS`.
- The active development service is on 28766; 28765 remains unused. PostgreSQL remained on the existing 5432 instance; no database clone or extra port was created.

**Next stage:** ChatGPT independently audits the committed fourth-batch report and evidence, especially G1–G4 source bindings and the R8 PG Publication receipt. Continue D0/market real-reference repair after that audit. Production Head switching, 28765, and production packaging remain separate gates.
