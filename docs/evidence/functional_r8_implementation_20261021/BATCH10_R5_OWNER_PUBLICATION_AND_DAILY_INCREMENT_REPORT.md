# BATCH10-R5 Owner Publication and Daily Increment Report

Date: 2026-10-23 (Asia/Shanghai)
Branch: `codex/v4-unified-development`
Requested baseline: `e5b499fc23faaf21a6c819d8f0bd18fa611952e6`
Starting remote branch HEAD verified through GitHub API: `37f104bf8c0d40152e8c9c11b8445dca9a5a84bd`. R5 was committed and pushed as `9d68ad114d86a77964e68946126f63481e236ab9`, then verified as the branch HEAD through the GitHub API. Direct `git fetch` initially failed at TLS negotiation; push succeeded using the alternate TLS backend.

## Correction to the prior audit

The 10/20 and 10/21 candidate JSON, all 20 target-day Owner payloads per date, and matching PG Owner facts were present under `G:/codex_tmp/v4_daily_candidate_chain_20261020`. The previous “candidate/Owner missing” statement came from checking the repository root; it was wrong. A token is the SHA-256 content fingerprint of the candidate, binding date, predecessor, source and Owner bytes, algorithm contracts and NON_PIT status. It is not an ingress credential. ReadIndex R1 and R2 are separate contracts; existing 10/21 R1 presence did not prove R2 or R8/D0 exact-token publication.

## Exact-token development PG publication

Both candidates validated and all 20/20 Owner files matched their candidate byte counts and hashes. ReadIndex R2 was prepared for each exact token. The first 10/20 28766 callback returned `READ_INDEX_TOKEN_NOT_PREPARED`; the candidate CAS rolled back. After R2 preparation, the same token retried and finalized. The aborted attempt remains in the append-only event history. Retry requires a verified callback-only abort, pending PG row, and exact predecessor restoration.

| Date | Candidate token | R8 | D0 | ReadIndex R2 | Stock/sector Priority Owner | D0 readback |
|---|---|---|---|---|---|---|
| 2026-10-20 | `a5b169a8cde60cc6ba86f1efbb7714020e578264bfea33634532ab407df70b70` | `PUBLISHED` | `PUBLISHED_DEV_ASOF_SOURCE_VERIFIED` | `REAL_PG_PASS` | PG readback PASS; 0/5,224 stock and 0/400 sector rows rankable because exact inputs are missing/invalid | 10,452 facts; 5,226 predicates; digest PASS; TRUE 141 / FALSE 5,033 / UNKNOWN 52 |
| 2026-10-21 | `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378` | `PUBLISHED` | `PUBLISHED_DEV_ASOF_SOURCE_VERIFIED` | `REAL_PG_PASS` | PG readback PASS; 936/5,224 stocks rankable; 0/400 sectors rankable under current dated-input gates | 10,448 facts; 5,224 predicates; digest PASS; Launch TRUE 78 / FALSE 5,098 / UNKNOWN 48; Recovery TRUE 28 / FALSE 5,147 / UNKNOWN 49 |

Writes targeted only `127.0.0.1:5432/market_research` candidate schemas. Both remain `AS_RECORDED=false`, `PIT_ELIGIBLE=false`, `production_accepted=false`. Formal Head, scheduler and 28765 were untouched.

## Lifecycle actual-bar boundary

`conserve_lifecycle_status_rows` already derives `actual_bar_present` from same-date RAW Owner IDs in this branch, so the source fix was not duplicated. Replayed exact PG-backed 10/21 Owner rows: RAW 5,216; lifecycle 5,224; normal actual-bar count 5,216. An in-memory negative case withheld one real RAW identity: status stayed `ACTUAL_TRADED`, while `actual_bar_present=false`, `status_conflict=true`, reason `RAW_BAR_RECEIPT_NOT_FOUND_FOR_DATE_AND_SECURITY`. A wrong-date RAW case was rejected. No real source row falsely claimed a bar.

## Focus Priority, Forward, and 10/22

- `V4_DAILY_RESEARCH_PRIORITY_R1` is an existing stock/sector ranking contract; exact-token 10/20 and 10/21 Owners were materialized and read back from PG. On 10/20 no rows ranked: 5,217 stocks had invalid price-coordinate proof and 79 sectors had invalid dated rotation/lifecycle inputs, with the rest unknown; on 10/21 936 stocks ranked while all sectors remained non-rankable on missing/invalid dated lifecycle inputs. The `/priority` compatibility API still has no operational Owner. This contract does not define Focus ranking and cannot substitute for it. 28766 `focus/priority` returns `SOURCE_INCOMPLETE / NO_OPERATIONAL_FOCUS_SUBPAGE_OWNER` for 10/21. The current Focus contract has no versioned ranking rule; formal Focus Priority is `CONTRACT_BLOCKED`, with no invented business ordering.
- The independent Forward validation cohort remains `WAIT_TRUE_FIRST_CAPTURE`. The visible 10/21 page says the first-capture deadline passed without a T0 capture and prohibits retrospective backfill; the as-of signal source, cohort Owner and first-freeze receipt remain absent.
- No 10/22 SourceIngress receipt was found. Read-only scan of 11,884 configured TDX `.day` files found latest last-record date 2026-10-08 (2 empty/malformed files). No 10/22 increment was fabricated.

## 28766 and visible page

28766 serves 10/21 token `14ee…`; context, Focus (3,975 objects), home, Priority and Forward routes were read. Focus Priority exposes the missing Owner; Forward returns `NO_AUTHORIZED_COHORT_OWNER`. Browser accessibility inspection of `/v4/research/focus` shows selected 10/21, 3,975 Focus rows, the historical NON_PIT notice and first-capture warning. PostgreSQL remained on 5432; 28766 was the only web listener; 28765 had no listener.

## Code and deferred scope

Code changes: safe R8 retry after a proven callback rollback, preserving the failed attempt; and completing the candidate release command's stated R8-then-D0 publication/readback sequence. `py_compile` and `git diff --check` passed. The focused bridge regression passed before the final D0 orchestration addition. Lifecycle correction was already present and was verified against exact PG Owner rows.

R6 market-trend date generalization, S02 source/performance work and D2 frozen-level rule remain deferred by the task card. Formal Focus Priority needs a versioned business rule before publication. This scoped development result is not production acceptance or external audit sign-off.

Evidence JSON: `docs/evidence/functional_r8_implementation_20261021/BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_EVIDENCE.json`.
