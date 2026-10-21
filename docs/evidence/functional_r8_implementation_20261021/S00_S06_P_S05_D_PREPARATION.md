# Functional R8 R2 first batch — baseline and bounded preparation

- Contract: `V4-FUNCTIONAL-R8-REPAIR-20261021/R2`.
- Task entry: Drive file `V4_FUNCTIONAL_R8_R2_FIRST_IMPLEMENTATION_BATCH_S00_S01_S03_20261021.md` (read 2026-10-21 Asia/Shanghai).
- Implementation branch and initial HEAD: `codex/v4-unified-development`, `36b0f968502f91b46407985764ad2fbd7c5d71fb`.
- Business code baseline: `6b02414cf5824e9e59a04c7decc3fc75713b083c`; the next two commits are plan/review documentation.
- Applicable records read before implementation: final R2 plan, its second review, R7 audit, R8 source repair spec R1, runtime performance R1, increment identity amendment R1.1, exact daily continuation R1, and Phase 0 R3.1 acceptance.

## S00 — frozen implementation baseline

| Dimension | Readback | State / permission |
|---|---|---|
| Git | Branch and HEAD equal the task entry; working tree initially had only untracked `.githooks/`, `config_back/`, and `script_back/`. | `CODE=BASELINE_CONFIRMED`; unrelated untracked paths are preserved. |
| Phase 0 | `docs/V4_PHASE0_FINAL_ACCEPTANCE_R3_1_20260925.md` and its hash-bound final receipt R5: `DEGRADED_PASS`; scanner status `NOT_APPLICABLE_UNTIL_V4_05`. | This task does not start a scanner. |
| 28766 | Existing preview PID 49884 was stopped before source refresh. The same candidate-only preview entrypoint was restarted from the current repo checkout during implementation; final readback PID 26256. | Only `127.0.0.1:28766` serves branch work. No 28765 listener was present. |
| PG | Listener PID 8640 at 5432. Read-only identity query returned `market_research`, database OID `646711`, PostgreSQL `180006`; no credential or DSN was logged. | Existing instance/database only; this batch issues no writes, schema changes, worker, or collector. |
| Formal state | `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json`, T0 `2026-10-09`, SHA-256 `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`. | The file remains unchanged. This is the accepted predecessor for S06-P G2. |
| Candidate state | Live 28766 `/api/v4/context`: T0 `2026-10-14`, token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`, `PIT_ELIGIBLE=false`, `production_accepted=false`, `formal_head_match=false`. Candidate metadata rebind SHA-256 `70aa8344e90401f73019b028edd3552afd5406bb68a95485f3a553688820b37e`. | Explicit successor candidate, `NON_PIT`; not promoted or relabeled. |
| TDX / source capture | No TDX source-root file was changed. No new daily source capture was run. | Read-only input boundary preserved; no unapproved capture cadence/storage was inferred. |
| Runtime inputs | The candidate's source cutoff is 10/14; source/Owner references remain those in its metadata rebind. | `CODE/NUMERIC` work can proceed on the candidate; no new data date is claimed. |

### Implementation impact and version matrix

| Change | Affected domain | Candidate identity treatment | Accepted-history treatment |
|---|---|---|---|
| S01 stable candidate market-risk payload digest | 28766 Priority BFF response, lifecycle and Focus reason caches | Cache keys include candidate metadata/source-binding revision; cache diagnostics are response metadata outside the business digest. | No accepted owner or head mutation. |
| S03 required finite, quality-admitted Priority fields | Priority rankability, score input and exclusion explanation | Recompute a candidate-only result from the same 10/14 input; preserve contract weights and sort order. | Do not append revised results to accepted history; require normal versioned repair admission before any later accepted use. |
| S06-P / S05-D | Planning and source/contract tracing only | Read-only evidence and proposals only. | No Head/Owner/episode change. |

## S06-P — bounded dual-reference and revision plan

**Current anchors.** Reference A is the actual accepted 10/09 Head above. Reference B is the 10/14 explicit successor candidate and its dated owner bindings. The two dates are not a direct numeric-equivalence pair. Reference B remains `NON_PIT`; its reconstructed latest-membership source must not be treated as an as-recorded universe.

**Prepared comparator.** For a later authorized increment, compare (1) fixed-T0 candidate output against an independent numeric/semantic calculator under identical input bindings, code/parameter versions, price coordinate and scope, and (2) prior accepted Head identity against the original accepted bytes. Report separately:

- G1: values and states over every object at fixed T0, including price/MA/return/profile, sector, Focus/D0/D2 and quality; no dropped records due to differing IDs.
- G2: prior accepted Owner/source SHA/Anchor/Episode/Focus identities and all prior references remain byte/identity stable; only the true accepted Head is authoritative for this check.
- G3: each new digest is independently recomputed from the exact old/new owner bytes, parameter and producer versions, input window and previous accepted reference.
- G4: ordinary APPEND computes only newly eligible sessions; a source/algorithm/parameter revision routes to a named range repair, never an ordinary append.

**Source-revision negative plan.** In an isolated engineering fixture, change bound source bytes without changing the binding and require the verifier to fail. Change a candidate's valid binding revision under the same context token and require a cache miss/new derived identity. Change date/token/producer/parameters/member window and require independent cache namespaces. Never mutate formal Owner bytes. No candidate PG namespace, DDL, DML, full replay or Head CAS is part of this preparation.

**Increment window.** No later candidate T0/source was produced in this batch. A future computation must start from the last independently valid candidate only when its predecessor chain is admitted; a formal append must instead start from the true accepted 10/09 predecessor and account for every eligible session. The 10/14 candidate cannot be promoted to skip the interval.

**Current state:** comparator and negatives prepared; runtime hotspot timings and independent census are in `FIRST_BATCH_REPORT.md` / `S03_PRIORITY_CENSUS_R5.json`. Actual increment, G1–G4 execution and write path remain `OPEN / WAIT_AUTHORIZATION`.

## S05-D — threshold provenance and exact-coordinate proposal

**Source finding.** `config/v4_r7_frozen_invalidation_contract_r2.json` version 2.0.0 defines only the comparator (`close <= frozen level`), required evidence, candidate-only scope and UNKNOWN behavior. It does not define how an episode's frozen level is generated. `src/workbench_analysis/r7_frozen_invalidation_v2.py` implements that comparator, not a level producer. `src/workbench_analysis/r6_reason_attribution.py` currently passes no current close, frozen level, basis, or actual-bar proof; the input remains UNKNOWN. R2 explicitly says the D2 comparator and breakout-episode rules do not supply the missing generation rule.

**Coordinate proposal for review (not implemented).** Freeze an explicit episode-start basis identity and use the local TDX affine-QFQ kernel (`tdx-affine-qfq-v0.2`) with the matching accepted GBBQ/source revision to express later actual closes in that same episode-start coordinate. A current/frozen basis mismatch, unsupported corporate action or unverified source remains UNKNOWN. This is consistent with the repository's exact affine kernel and the date-specific factor language in `config/v4_15_forward_projection_r20r1r2_v1.json`; it does not authorize external adjustment. The applicable rounding, basis identity construction and single-target factor binding still require exact contract text before code.

**Minimum versioned decision record proposed:** `V4_D2_FROZEN_INVALIDATION_LEVEL_R1`. It must choose and bind (a) the episode class and the business rule that generates the level, with field/window/parameters; (b) the one-time freeze event and effective date; (c) source Owner SHA, `available_at`, producer and parameter versions; (d) exact TDX price-coordinate and event/action transport; (e) equality boundary and state precedence; and (f) replay, missing-bar, unsupported-action, same-day rerun, re-entry and historical non-backfill cases. Until the business rule in (a) is explicitly adjudicated, the proposal is `BLOCK_CONTRACT`, not an implementation instruction.

**Impact / stop line.** Preserve the 875 prior episodes without a frozen level as UNKNOWN; do not backfill or relabel them. S05-I remains `BLOCK_CONTRACT`. This finding does not block S01/S03, S02/S04, or preparation of S06-P.
