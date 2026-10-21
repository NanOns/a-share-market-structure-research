# Fourth Batch Report — R8 Functional Increment (2026-10-21)

## Result

**Status: development append PASS; independent external audit and D0/market-source gates remain open.** The 2026-10-15 real-source daily increment now completed the full candidate chain: BaoStock retry and TDX reconciliation, exact day freeze, Owner computation and PG payload readback, independent G1–G4 comparator, append-only PG Publication record, development Head CAS, and same-token HTTP acceptance on 28766. The accepted candidate token is `ed65f0ff84d2e7f0ed1c7a3c2663a53ee364b951ba8822718ec2ae6dc5e00ed2`.

The work is candidate-only and `NON_PIT`. The formal Head remains 2026-10-09. No production Head, production service port 28765, scanner, or final production package was changed or accepted. Full machine-readable evidence and copied source receipts are indexed in [ARTIFACT_INDEX.json](FOURTH_BATCH_ARTIFACTS/ARTIFACT_INDEX.json).

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
- PG Publication ledger: **one row**, exact readback PASS, append-only trigger present; database `127.0.0.1:5432/market_research`, OID `646711`, PostgreSQL 18.6.
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

The development preview was restarted on the **only** development web port, `127.0.0.1:28766`, after CAS so the server loaded the new exact candidate token. The following routes returned HTTP 200 with `T0=2026-10-15` and the same token: `/api/v4/context`, `/api/operations/status`, `/api/v4/home`, `/api/v4/market`, `/api/v4/stocks`, `/api/v4/sectors`, `/api/v4/focus`, and `/api/v4/forward/statistics`.

The PostgreSQL read index was built offline for the exact token and read back 5,226 stocks, 400 sectors, 3,355 Focus rows, and 165 radar rows. Priority was precomputed offline for 5,226 stocks (701 rankable) and 400 sectors (121 rankable). The first offline computation took 16.263 seconds. Two same-token HTTP priority reads then returned 200 in 171.703 ms and 151.321 ms; each reported `projection_rank_compute_ms=0.0` and identical payload SHA. The precompute now selects snapshots by token, preserving the prior 10/14 snapshot when a later date is added. Candidate lifecycle reconstruction no longer has a 10/14 date cap.

## D0, market source, and limits

The 10/15 D0/Prewatch/market computation completed but correctly remains source-limited: D0 reports 64 TRUE and 5,162 UNKNOWN, its seal state is null, and market trend remains `UNKNOWN_REFERENCE_PATH_NOT_COMPLETE_AT_T0` (`market_status=SOURCE_INCOMPLETE`). No composite market permission or D0 seal permission was inferred. Repairing those actual-reference inputs remains the next engineering scope; this candidate append does not claim that gate is closed.

## Verification and handoff

- G1–G4 business comparator: PASS.
- Source ingress exact-value readback and idempotent replay: PASS for 5 receipts / 27,832 bars, as documented in `PG_SOURCE_INGRESS_EXACT_READBACK_RECEIPT.json`.
- Candidate Head, PG ledger row, read index, period oracle, rollback proof, priority snapshot, BaoStock receipts/raw responses, and live 28766 route measurements are committed in `FOURTH_BATCH_ARTIFACTS`.
- The active development service is on 28766; 28765 remains unused. PostgreSQL remained on the existing 5432 instance; no database clone or extra port was created.

**Next stage:** ChatGPT independently audits the committed fourth-batch report and evidence, especially G1–G4 source bindings and the R8 PG Publication receipt. Continue D0/market real-reference repair after that audit. Production Head switching, 28765, and production packaging remain separate gates.
