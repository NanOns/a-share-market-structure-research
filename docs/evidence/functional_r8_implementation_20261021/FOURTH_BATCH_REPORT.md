# Fourth Batch Report — R8 Functional Increment (2026-10-21)

## Result

**Status: PARTIAL / OPEN; ready for independent audit of the implemented controls and captured evidence.** The batch completed a real PostgreSQL TDX SourceIngress write and idempotency replay, tightened G1–G4 evidence checks, hardened D0 and market-source permission, versioned candidate breadth delta, and removed Priority ranking work from the HTTP request path when a valid offline snapshot exists. The requested complete post-10/14 operational append was **not** achieved: no verified R8 source-to-Owner-to-Publication-to-development-Head/CAS pipeline existed for the new dates, and the only newly ingested source family was TDX raw daily bars. No missing business facts or Head transitions were fabricated.

No formal/production Head was modified, no production acceptance was asserted, and no 28765 service was started or used. The report and evidence are intended for the next independent ChatGPT audit.

## Baseline and applicable contract

- Repository branch: `codex/v4-unified-development`.
- Audit starting commit: `4c65039b7935ea2396740df8552045afcd8afb61`.
- The task card and the 2026-10-18 development high-privilege SOT R2 were read before database work. SOT R2 authorizes bounded development database DDL/DML, migration, backfill, recompute and development Head/CAS validation; no repeated database write authorization was requested.
- Applicable local source repair, runtime performance, identity parity and Phase 0 documents were reviewed before implementation. Phase 0 result remains `DEGRADED_PASS`; no scanner work was started.
- Updated `AGENTS.md` clauses 12–13 to reflect SOT R2 and keep the production Head / 28765 boundary explicit.
- Historical and TDX source roots remain unmodified. The TDX distribution was captured into G-drive temporary storage only.

## Real source and PostgreSQL evidence

A bounded capture used the existing official TDX daily-source adapter. The provider package was dated 2026-10-21, with provider update time 15:58:50 China time; capture completed at `2026-10-21T09:35:26Z` (17:35:26 China time). The package was 549,730,276 bytes with SHA-256 `0404bbaeb985b2409a99dfcfe2c67b00e5dd574378105c408486183e9e058ede`. TDX source-root writes: 0.

The package yielded the following daily bars. 10/15, 10/16, 10/19 and 10/20 are explicitly `RECONSTRUCTED_NON_PIT`; 10/21 is `CAPTURED_AFTER_CLOSE_NON_PIT`. None is labeled PIT or AS_RECORDED.

| Trade date | Rows | Evidence class |
| --- | ---: | --- |
| 2026-10-15 | 5,565 | RECONSTRUCTED_NON_PIT |
| 2026-10-16 | 5,567 | RECONSTRUCTED_NON_PIT |
| 2026-10-19 | 5,564 | RECONSTRUCTED_NON_PIT |
| 2026-10-20 | 5,568 | RECONSTRUCTED_NON_PIT |
| 2026-10-21 | 5,568 | CAPTURED_AFTER_CLOSE_NON_PIT |

A real transaction created development schema `v4_r8_batch04_source_ingress` and its bounded receipt/bar tables, then wrote 5 receipts and 27,832 bars. The write target was `127.0.0.1:5432/market_research`, database OID `646711`, PostgreSQL `18.6`; the task connection reported role `postgres`. The second run read back all five dates and was idempotent: counts remained 5 receipts / 27,832 bars and every receipt insert reported false. The two receipts are summarized in `FOURTH_BATCH_EVIDENCE.json`; full run receipts remain under `G:/codex_tmp/r8_fourth_batch/`.

This transaction is **source ingress only**. It does not create canonical Owners, factor outputs, R8 Publication records or any Head. Before writes, the existing formal Head remained 2026-10-09 and preview T0 was 2026-10-14. The checked R8 Publication/Head path had no candidate publication/head records to advance. Post-write, no formal or development Head/CAS transition was made. Existing preview remains 10/14, `production_accepted=false`.

## G1–G4 independent evidence checks

The R8 append comparator is now `V4_R8_CANDIDATE_APPEND_COMPARATOR_R2` and verifies evidence from bytes instead of accepting caller assertions:

- **G1:** the comparator retains separately reportable gate outcomes; memory-only vectors do not establish bound source evidence.
- **G2:** requires independently bound reference and candidate historical-identity bytes, validates root-contained paths, byte counts and SHA-256, then checks byte identity.
- **G3:** recomputes the candidate digest from the verified bound source bytes and declared append parameters/window/previous reference; a caller-supplied matching digest alone is insufficient.
- **G4:** requires a bound `V4_R8_REAL_APPEND_PG_RECEIPT_R1` receipt for the real database append. Boolean claims or a date alone fail closed.

Targeted tests include a positive G2/G3 byte-binding fixture, a source tamper negative case, and fail-closed memory-only/G4-without-PG-receipt cases. This establishes comparator behavior, **not** completion of all four business gates on a real post-10/14 R8 publication: G4 and full append remain OPEN because no verified Owner/Publication/development-Head CAS operation was performed.

## D0, market source and breadth

- `r6_reason_attribution.py` no longer treats a date-only clock as midnight or caller booleans/fake hashes as permission proof. D0 permission remains `SEAL_PERMISSION_UNPROVEN` until an actual verified PG Owner/Publication binding is present. Day-level T0 comparison uses the parsed date.
- `r6_candidate_market_stress.py` no longer accepts caller-shaped permission evidence. Trend stays `UNKNOWN` while its real reference path is incomplete. Four-axis facts are not promoted to formal composite permission.
- Added versioned breadth contract `S02_ADVANCERS_SHARE_DELTA3_R1`, version `1.0.0`, algorithm `ADVANCERS_SHARE_DELTA3`; it reports the difference in advancing share, with status `DEV_CANDIDATE_VERSIONED`. Existing SIGN remains diagnostic.
- Actual preview still reports `UNKNOWN_REFERENCE_PATH_NOT_COMPLETE_AT_T0`; D0 seal state is null/unproven. No market permission is inferred from that output.

## Priority precompute and 28766 acceptance

Added candidate-only offline materialization using `R8_CANDIDATE_PRIORITY_OFFLINE_PRECOMPUTE_R1` and a versioned identity that binds context token, T0, candidate SHA, owner identities, parameters, producer, lifecycle inputs and session window. Snapshot writes are atomic in the G-drive candidate cache. With `R8_REQUIRE_PRIORITY_PRECOMPUTE=1`, a missing or invalid snapshot fails closed instead of computing rankings inside an HTTP request.

The fixed preview remains `T0=2026-10-14`, formal Head 2026-10-09. Offline computation produced 5,225 stocks (967 rankable, 4,258 excluded) and 400 sectors (141 rankable, 259 excluded); snapshot size 2,202,155 bytes, SHA-256 `26dcb19dabe555a23b32d643aa51fd791241bba43b67ba1233eb7464a78147b3`. Cached offline rerun took 328.225ms.

On the sole allowed development web slot `127.0.0.1:28766`, Priority cold and hot HTTP calls returned 200/READY in 312.243ms and 206.926ms, both with `projection_rank_compute_ms=0`, 967 rankable stocks, stable payload digest `80c6430b8205a271d790e3a1a105bfa6bfa26ba59687879af12eb2e04b716191`, T0 10/14, `production_accepted=false`. A cold-start probe with the snapshot payload digest deliberately corrupted returned HTTP 400 / `R8_PRIORITY_PRECOMPUTE_REQUIRED` in 166.244ms; the original snapshot bytes were restored and their SHA verified. This confirms the HTTP path does not substitute an in-request ranking when persisted evidence fails validation.

| 28766 route | HTTP | Time (ms) | Result |
| --- | ---: | ---: | --- |
| `/api/operations/status` | 200 | 2.21 | status endpoint reachable |
| `/api/v4/home` | 200 | 918.60 | READY |
| `/api/v4/market` | 200 | 141.44 | READY |
| `/api/v4/stocks` | 200 | 307.56 | READY, 5,225 |
| `/api/v4/sectors` | 200 | 508.81 | READY, 400 |
| `/api/v4/focus` | 200 | 4,383.26 | READY, 3,247 |
| `/api/v4/forward/statistics` | 200 | 3,725.03 | READY |

The endpoint acceptance confirms the existing 10/14 preview and its serving paths only. It does not represent a new date becoming visible in the product.

## Verification and remaining acceptance

- Targeted regression set: **45 passed** (`test_v4_functional_r8_third_batch.py`, `test_v4_functional_r8_s01_s03.py`, `test_v4_r6_risk_priority.py`).
- Python byte-compilation for changed modules and helper scripts passed during implementation.
- `git diff --check` passed.
- Final listener check: only `127.0.0.1:28766` was listening for this app (PID 4168). `127.0.0.1:28765` was not listening. PostgreSQL remained on `127.0.0.1:5432`; no separate DB instance or port was created.

### Blocking conditions for a complete daily increment

1. Supply or repair the verified producer chain for all required daily source families, corporate-action/price-adjustment basis and effective security lifecycle/identity; the TDX raw-bar ingress alone cannot satisfy Core/Factor/Profile/Sector/Priority/Focus/Forward contracts.
2. Establish the R8 PG source-to-Owner/Publication schema and provenance path that independently binds the source receipts, then run a bounded development Owner/Publication transaction and development Head/CAS validation without touching formal/production Head.
3. Run G1–G4 against that actual independently bound append and preserve historical identity bytes. Until then, the new TDX ingress is an evidenced partial increment, not a closed R8 append.
4. Rebuild and inspect all dependent downstream products and D0/market permission after the actual owner path is present. Current D0/Trend states deliberately remain unproven/UNKNOWN.

**Next stage:** resolve the producer/source-family and R8 Publication/Head lineage gaps as a separately auditable development task, then rerun actual PG append + G1–G4. Any later request for production Head, 28765 switch or final package remains a separate release gate.
